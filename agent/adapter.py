"""One interface over three model paths (T4): local (Ollama), cloud (OpenRouter), claude (Anthropic).
call() takes OpenAI-format messages and tools. It returns text, tool calls, tokens, latency and cost, plus
"message": the assistant turn to append to messages to continue on the same path. Plain HTTP (D40).
The cap and the spend log live in agent/spend.py (D46)."""
import ipaddress, json, os, socket, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from agent import spend

DEFAULT = {"local": "qwen3.5:9b-q4_K_M", "cloud": "qwen/qwen3.5-9b", "claude": "claude-sonnet-5-5"}
NUM_CTX = 16384        # fixed; truncate/shift off so Ollama refuses or stops rather than cutting (D40, D95)
RETRIES = 3            # D42: waits of 2, 4, 8 s, or the server's retry-after
ENV = Path(__file__).resolve().parent.parent / ".env"

def key(name):
    lines = ENV.read_text().splitlines() if ENV.exists() else []
    value = os.environ.get(name) or next((l.split("=", 1)[1].strip() for l in lines if l.startswith(name + "=")), "")
    if not value:
        raise RuntimeError(f"{name} is not set (environment or .env)")
    return value

def post(url, body, headers, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:          # caught before URLError, its parent class
            err, wait = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}", e.headers.get("retry-after")
            if e.code < 500 and e.code not in (408, 409, 429):
                raise RuntimeError(err)
        except (urllib.error.URLError, TimeoutError) as e:
            err, wait = str(e), None
        if attempt == RETRIES:
            raise RuntimeError(f"{err} (after {RETRIES} retries)")
        time.sleep(min(60, float(wait)) if wait and wait.replace(".", "", 1).isdigit() else 2 ** (attempt + 1))

def function_calls(raw):
    """OpenAI-format tool calls as {id, name, args}. Ollama sends arguments as an object, the others as JSON text."""
    return [{"id": c.get("id") or f"call_{i}", "name": c["function"]["name"],
             "args": c["function"]["arguments"] if isinstance(c["function"]["arguments"], dict)
             else json.loads(c["function"]["arguments"] or "{}")} for i, c in enumerate(raw or [])]

def send_local(model, messages, tools, max_tokens):
    host = key("OLLAMA_HOST")
    url = urllib.parse.urlsplit(host if "://" in host else "http://" + host)
    for info in socket.getaddrinfo(url.hostname, None):          # the box is home-network only (D11)
        if not (ip := ipaddress.ip_address(info[4][0].split("%")[0])).is_private and not ip.is_loopback:
            raise RuntimeError(f"refusing {url.hostname}: {ip} is not a home-network address")
    r = post(f"http://{url.hostname}:{url.port or 11434}/api/chat", {
        "model": model, "messages": messages, "tools": [{"type": "function", "function": t} for t in tools],
        "stream": False, "truncate": False, "shift": False, "options": {"num_ctx": NUM_CTX, "num_predict": max_tokens}}, {}, 1800)
    if r.get("done_reason") == "length" and r.get("eval_count", 0) < max_tokens:   # an over-long prompt is a 400
        raise RuntimeError(f"the reply ran out of context at num_ctx={NUM_CTX} after {r['prompt_eval_count']} prompt tokens")
    return {"text": r["message"].get("content", ""), "tool_calls": function_calls(r["message"].get("tool_calls")),
            "input_tokens": r.get("prompt_eval_count", 0), "output_tokens": r.get("eval_count", 0),
            "stop": r.get("done_reason"), "message": r["message"]}

def send_cloud(model, messages, tools, max_tokens):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,       # pinned to one host (D39)
            "provider": {"order": ["deepinfra"], "allow_fallbacks": False, "require_parameters": True},
            **({"tools": [{"type": "function", "function": t} for t in tools]} if tools else {})}
    r = post("https://openrouter.ai/api/v1/chat/completions", body,
             {"Authorization": "Bearer " + key("CLOUD_QWEN_API_KEY")}, 120)
    choice, usage = r["choices"][0], r.get("usage", {})
    msg = choice["message"]
    return {"text": msg.get("content") or "", "tool_calls": function_calls(msg.get("tool_calls")),
            "input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0),
            "stop": choice.get("finish_reason"), "message": msg,
            "host": r.get("provider"), "billed_usd": usage.get("cost")}       # to cross-check spend.PRICE

def send_claude(model, messages, tools, max_tokens):
    body = {"model": model, "max_tokens": max_tokens, "messages": [
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}]}
        if m["role"] == "tool" else m for m in messages if m["role"] != "system"]}
    if system := "".join(m["content"] for m in messages if m["role"] == "system"):
        body["system"] = system
    if tools:
        body["tools"] = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["parameters"]}
                         for t in tools]
    r = post("https://api.anthropic.com/v1/messages", body,
             {"x-api-key": key("ANTHROPIC_API_KEY"), "anthropic-version": "2026-10-21"}, 120)
    calls = [{"id": b["id"], "name": b["name"], "args": b["input"]} for b in r["content"] if b["type"] == "tool_use"]
    return {"text": "".join(b["text"] for b in r["content"] if b["type"] == "text"), "tool_calls": calls,
            "input_tokens": r["usage"]["input_tokens"], "output_tokens": r["usage"]["output_tokens"],
            "stop": r["stop_reason"], "message": {"role": "assistant", "content": r["content"]}}   # thinking kept

def call(path, messages, tools=(), model=None, max_tokens=1024, budget="dev"):
    row = {"path": path, "model": model or DEFAULT[path], "budget": budget, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}
    spend.check(row, [messages, list(tools)], max_tokens)       # raises spend.CapReached; nothing is sent
    start, send = time.monotonic(), {"local": send_local, "cloud": send_cloud, "claude": send_claude}[path]
    try:
        out = {**row, **send(row["model"], messages, list(tools), max_tokens)}
    except Exception:    # no usage came back, so the row records $0
        spend.log("error", {**row, "latency_s": round(time.monotonic() - start, 2)})
        raise
    out["latency_s"] = round(time.monotonic() - start, 2)
    out["cost_usd"] = 0 if path == "local" else spend.cost(out["model"], out["input_tokens"], out["output_tokens"])
    spend.log("ok", out)
    return out
