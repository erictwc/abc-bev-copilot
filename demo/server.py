"""The hosted demo (T14): one page, a question box and a model dropdown. Standard library only (D114).

Claude and cloud Qwen answer live through agent.loop.ask(budget="demo"), so every call goes through the
adapter's spend cap (D115). Local Qwen is never called: it shows the recorded answers from the latest
committed local eval run, labelled as replays (D11). Keys stay on the server, read by the adapter from
the environment; the browser only ever sees answers.

Live questions pass these checks before any model call (D116). The limits are constants, so changing
one is a reviewed commit:
  - DEMO_LIVE=off pauses live answers (replays still work)
  - one question at a time per visitor, 5 per 10 minutes, 20 per day
  - 100 live questions a day for the whole site, at most 2 running at once
  - a question of at most 500 characters
Every live request, admitted or refused, is a line in logs/demo_requests.jsonl, with the visitor's IP
hashed. Run with: python -m demo.server [--port 7860] [--host 127.0.0.1]
"""
import argparse, hashlib, json, os, secrets, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent import loop, spend

ROOT = Path(__file__).resolve().parent.parent
PAGE = Path(__file__).resolve().parent / "index.html"
RESULTS = ROOT / "evals" / "results"
REQUEST_LOG = ROOT / "logs" / "demo_requests.jsonl"

LIVE = {"claude": "Claude Sonnet 5.5", "cloud": "Qwen 3.5 9B, cloud"}
MAX_CHARS = 500
PER_VISITOR = [(600, 5), (86400, 20)]   # (window in seconds, questions)
SITE_PER_DAY = 100
MAX_RUNNING = 2
MAX_BODY = 4096
SALT = os.environ.get("DEMO_LOG_SALT") or secrets.token_hex(16)   # random per process if unset


def now_utc():
    return datetime.now(timezone.utc)


def log_request(entry):
    REQUEST_LOG.parent.mkdir(exist_ok=True)
    with REQUEST_LOG.open("a") as f:
        f.write(json.dumps({"timestamp": now_utc().isoformat(timespec="seconds"), **entry}) + "\n")


def admitted_today():
    """Live questions admitted so far today (UTC), from the request log, so a restart keeps the count."""
    if not REQUEST_LOG.exists():
        return 0
    day = now_utc().strftime("%Y-%m-%d")
    count = 0
    for line in REQUEST_LOG.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        count += e.get("admitted") is True and e.get("timestamp", "").startswith(day)
    return count


class Limiter:
    """Per-visitor windows, one question in flight per visitor, a daily site total and a concurrency cap."""

    def __init__(self, clock=time.time, site_today=0):
        self.clock, self.lock = clock, threading.Lock()
        self.hits, self.running = defaultdict(deque), set()
        self.day, self.site = time.strftime("%Y-%m-%d", time.gmtime(clock())), site_today

    def acquire(self, who):
        """None if admitted (call release(who) afterwards), else (http status, message for the visitor)."""
        with self.lock:
            t = self.clock()
            day = time.strftime("%Y-%m-%d", time.gmtime(t))
            if day != self.day:
                self.day, self.site = day, 0
            if who in self.running:
                return 429, "Your previous question is still running. Wait for its answer, then ask again."
            hits = self.hits[who]
            while hits and hits[0] <= t - max(w for w, _ in PER_VISITOR):
                hits.popleft()
            for window, limit in PER_VISITOR:
                if sum(1 for h in hits if h > t - window) >= limit:
                    span = "10 minutes" if window == 600 else "day"
                    return 429, (f"You have reached the demo's limit of {limit} live questions per {span}. "
                                 "The recorded local runs still work.")
            if self.site >= SITE_PER_DAY:
                return 429, ("The demo has answered its {} live questions for today. Live answers resume at "
                             "midnight UTC; the recorded local runs still work.").format(SITE_PER_DAY)
            if len(self.running) >= MAX_RUNNING:
                return 503, "Other questions are running right now. Try again in a minute."
            hits.append(t)
            self.running.add(who)
            self.site += 1
            return None

    def release(self, who):
        with self.lock:
            self.running.discard(who)


def latest_local_run():
    """Replays: the newest local eval run (a *_local_*.jsonl not ending in _judged/_rescored)."""
    runs = sorted(p for p in RESULTS.glob("*_local_*.jsonl") if not p.stem.endswith(("_judged", "_rescored")))
    if not runs:
        return None, []
    path = runs[-1]
    cases = []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        cases.append({"id": row["id"], "passed": row["score"]["pass"], "result": public(row["result"])})
    return path.name, cases


def public(r):
    """The fields of an ask() result the page shows."""
    keep = ("question", "path", "model", "answer", "confidence", "flags", "evidence", "stopped", "steps",
            "input_tokens", "output_tokens", "cost_usd", "latency_s")
    return {k: r.get(k) for k in keep}


def visitor(handler, hops):
    """The visitor's IP. Behind the host's proxy (DEMO_PROXY_HOPS > 0) it is that many entries from the right
    of X-Forwarded-For, which the proxy appends to; anything to its left is whatever the client sent."""
    forwarded = [p.strip() for p in handler.headers.get("X-Forwarded-For", "").split(",") if p.strip()]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops], len(forwarded)
    return handler.client_address[0], len(forwarded)


def make_handler(limiter, replays, ask=loop.ask):
    run_file, cases = replays
    hops = int(os.environ.get("DEMO_PROXY_HOPS", "0"))

    class Handler(BaseHTTPRequestHandler):
        server_version = "abc-bev-demo"
        sys_version = ""

        def send(self, status, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):      # no IPs in stdout; the request log has hashed ones
            pass

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/api/config":
                return self.send(200, {
                    "live": os.environ.get("DEMO_LIVE", "on") != "off", "models": LIVE,
                    "max_chars": MAX_CHARS, "per_visitor": PER_VISITOR, "site_per_day": SITE_PER_DAY,
                    "demo_spent_usd": round(spend.month_spend("demo"), 2), "demo_cap_usd": spend.CAP_USD["demo"],
                    "replay_file": run_file})
            if self.path == "/api/replays":
                return self.send(200, {"file": run_file, "cases": cases})
            if self.path == "/healthz":
                return self.send(200, {"ok": True})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/ask":
                return self.send(404, {"error": "not found"})
            ip, n_forwarded = visitor(self, hops)
            entry = {"visitor": hashlib.sha256((SALT + ip).encode()).hexdigest()[:16], "forwarded": n_forwarded}
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    raise ValueError("request too large or empty")
                body = json.loads(self.rfile.read(size))
                question, model = str(body.get("question", "")).strip(), body.get("model")
            except (ValueError, AttributeError) as e:
                log_request({**entry, "admitted": False, "refused": f"bad request: {e}"})
                return self.send(400, {"error": "Send a JSON body with a question and a model."})
            entry.update(model=model, question=question[:MAX_CHARS + 50])
            refusal = None
            if model not in LIVE:
                refusal = 400, "Pick Claude or cloud Qwen for a live answer."
            elif not question:
                refusal = 400, "Type a question first."
            elif len(question) > MAX_CHARS:
                refusal = 400, f"Keep the question under {MAX_CHARS} characters."
            elif os.environ.get("DEMO_LIVE", "on") == "off":
                refusal = 503, "Live answers are paused right now. The recorded local runs still work."
            else:
                refusal = limiter.acquire(entry["visitor"])
            if refusal:
                log_request({**entry, "admitted": False, "refused": refusal[1]})
                return self.send(refusal[0], {"error": refusal[1]})
            try:
                r = ask(question, path=model, budget="demo")
            except Exception as e:      # ask() handles model and tool errors itself; this is a last resort
                log_request({**entry, "admitted": True, "error": f"{type(e).__name__}: {e}"})
                return self.send(500, {"error": "Something went wrong on the server. Try again later."})
            finally:
                limiter.release(entry["visitor"])
            log_request({**entry, "admitted": True, "stopped": r["stopped"], "steps": r["steps"],
                         "cost_usd": r["cost_usd"], "latency_s": r["latency_s"]})
            out = public(r)
            if r["stopped"] == "spend_cap":
                out["answer"] = ("This month's demo budget is used up, so live answers are paused until next month. "
                                 "The recorded local runs still work.")
            self.send(200, out)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    replays = latest_local_run()
    server = ThreadingHTTPServer((a.host, a.port), make_handler(Limiter(site_today=admitted_today()), replays))
    print(f"demo on http://{a.host}:{a.port}  replays from {replays[0]}  live {os.environ.get('DEMO_LIVE', 'on')}",
          flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
