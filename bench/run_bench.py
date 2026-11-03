"""Prefill and decode benchmark for the GEEKOM box (ticket T3).

Sends requests to the Ollama server at OLLAMA_HOST and appends one row per
measured run to bench/results.csv (D38). The timings are Ollama's own
server-side fields (D34):

- prefill tokens/s = prompt_eval_count / prompt_eval_duration
- decode tokens/s  = eval_count / eval_duration

Standard library only. The only network call goes to OLLAMA_HOST, and the script
refuses any address that is not private or loopback: the box is home-network
only (D11).

Ollama skips prompt tokens it has cached, which would make prefill look instant.
So every request starts with a fresh random nonce, and a run whose prompt count
comes back short is an error, never a row (D34).

Per model and prompt length (D36, D37): warm-up runs, which also tune the filler
prompt to its target token count and are discarded, then the measured runs.
"""

import argparse
import csv
import ipaddress
import json
import os
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from random import Random

MODELS = ["qwen3.5:4b-q4_K_M", "qwen3.5:9b-q4_K_M", "qwen3:14b-q4_K_M"]   # D35
PROMPT_TOKENS = [512, 2048, 8192]                                         # D36
GEN_TOKENS = 128
CTX_MARGIN = 64        # num_ctx = prompt + GEN_TOKENS + CTX_MARGIN, so the prompt is never cut
REPEATS = 3                                                               # D37
TOLERANCE = 0.03       # a tuned prompt is within 3% of its target, and never over num_ctx
MAX_TUNING = 4
RETRIES = 2           # server errors (HTTP 5xx) retried per request, 10 s apart
TIMEOUT_S = 3600       # an 8k prefill on the 14B can take many minutes on this CPU
HOST_LABEL = "GEEKOM-A5"
COLUMNS = ["timestamp", "host", "ollama_version", "model", "quant", "size_gb", "num_ctx",
           "prompt_tokens", "gen_tokens", "repeat", "prefill_tps", "decode_tps", "load_s"]

# Plain English filler. Its meaning does not matter, only its length.
WORDS = ("the order ship week case pallet route truck dock store shelf count plan "
         "line batch crate label north south east west early late full half open "
         "closed small large fresh cold dry clean quiet steady river field stone "
         "window garden morning evening paper table chair lamp road bridge hill").split()


def ollama_base(cli_host):
    """The base URL from --host, the environment or .env, in that order."""
    host = cli_host or os.environ.get("OLLAMA_HOST", "")
    env = Path(__file__).resolve().parent.parent / ".env"
    if not host and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OLLAMA_HOST="):
                host = line.split("=", 1)[1].strip().strip('"')
    if not host:
        sys.exit("OLLAMA_HOST is not set (environment or .env), and no --host was given")
    if "://" not in host:
        host = "http://" + host       # Ollama's own format allows a bare host:port
    url = urllib.parse.urlsplit(host)
    port = url.port or 11434
    return url.hostname, f"{url.scheme}://{url.hostname}:{port}"


def require_home_network(hostname):
    """Exit unless every address the name resolves to is private or loopback."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        sys.exit(f"cannot resolve {hostname}: {e}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not (ip.is_private or ip.is_loopback):
            sys.exit(f"refusing {hostname}: {ip} is not a home-network address")


def call(base, path, body=None):
    """One request. A server error (5xx) carries no timings, so it is retried, not recorded."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    for attempt in range(1, RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace").strip()
            if e.code < 500 or attempt > RETRIES:
                sys.exit(f"{path}: HTTP {e.code}: {msg}")
            print(f"{path}: HTTP {e.code}: {msg} (retry {attempt} of {RETRIES})", file=sys.stderr, flush=True)
            time.sleep(10)


def filler(n_words):
    rng = Random(n_words)
    return " ".join(rng.choice(WORDS) for _ in range(n_words))


def generate(base, model, n_words, num_ctx):
    """One raw request (no chat template) with a fresh nonce at the very start."""
    prompt = f"Run {secrets.token_hex(8)}. " + filler(n_words)
    return call(base, "/api/generate", {
        "model": model, "prompt": prompt, "raw": True, "stream": False, "keep_alive": "15m",
        "options": {"num_ctx": num_ctx, "num_predict": GEN_TOKENS, "temperature": 0, "seed": 42},
    })


def tune(base, model, target, num_ctx):
    """Warm-up runs, discarded: find a filler length within TOLERANCE of target tokens."""
    n_words = int(target / 1.3)
    for _ in range(MAX_TUNING):
        got = generate(base, model, n_words, num_ctx)["prompt_eval_count"]
        if abs(got - target) <= TOLERANCE * target and got + GEN_TOKENS <= num_ctx:
            return n_words, got
        if got < 0.5 * n_words:      # every filler word is at least one token
            sys.exit(f"{model}: only {got} prompt tokens for {n_words} words (prefix cache?)")
        n_words = max(1, round(n_words * min(2.0, target / got)))
    sys.exit(f"{model}: could not tune a {target}-token prompt (last count {got})")


def unload(base, model):
    call(base, "/api/generate", {"model": model, "keep_alive": 0})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", help="overrides OLLAMA_HOST")
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--prompt-tokens", nargs="+", type=int, default=PROMPT_TOKENS)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--host-label", default=HOST_LABEL, help="written to the CSV; never an address")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results.csv"))
    args = ap.parse_args()

    hostname, base = ollama_base(args.host)
    require_home_network(hostname)
    version = call(base, "/api/version")["version"]
    tags = {m["name"]: m for m in call(base, "/api/tags")["models"]}
    missing = [m for m in args.models if m not in tags]
    if missing:
        sys.exit("not pulled on the box: " + ", ".join(missing) + "\nrun: ollama pull <model>")

    out = Path(args.out)
    new_file = not out.exists()
    with out.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        for model in args.models:
            info = tags[model]
            for target in args.prompt_tokens:
                num_ctx = target + GEN_TOKENS + CTX_MARGIN
                n_words, expected = tune(base, model, target, num_ctx)
                for rep in range(1, args.repeats + 1):
                    r = generate(base, model, n_words, num_ctx)
                    if r["prompt_eval_count"] < (1 - TOLERANCE) * expected:
                        sys.exit(f"{model} {target}: only {r['prompt_eval_count']} of ~{expected} "
                                 "prompt tokens were evaluated (prefix cache or truncation)")
                    row = {
                        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "host": args.host_label,
                        "ollama_version": version,
                        "model": model,
                        "quant": info["details"]["quantization_level"],
                        "size_gb": round(info["size"] / 1e9, 2),
                        "num_ctx": num_ctx,
                        "prompt_tokens": r["prompt_eval_count"],
                        "gen_tokens": r["eval_count"],
                        "repeat": rep,
                        "prefill_tps": round(r["prompt_eval_count"] / r["prompt_eval_duration"] * 1e9, 2),
                        "decode_tps": round(r["eval_count"] / r["eval_duration"] * 1e9, 2),
                        "load_s": round(r.get("load_duration", 0) / 1e9, 2),
                    }
                    writer.writerow(row)
                    f.flush()
                    print(f"{model} ctx={num_ctx} rep={rep}: prefill {row['prefill_tps']} tok/s, "
                          f"decode {row['decode_tps']} tok/s", flush=True)
            unload(base, model)    # 16 GB of RAM: free it before the next model loads


if __name__ == "__main__":
    main()
