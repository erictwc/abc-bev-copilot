"""The spend log and the monthly cap (T4, D5). agent/adapter.py calls check() before every model call
and log() after it, so every call, including refused, failed and free local ones, is a row in
logs/spend.csv (D41).

A paid call is refused, never sent, if this month's logged spend plus the most the call could cost
would pass its budget's cap (D44, D45). A dev call counts every row in the log; a demo call counts
only demo rows, so the hosted demo has its own $20 a month (D115). Changing a cap or a price is a
reviewed commit, not a setting.
"""
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

SPEND_LOG = Path(__file__).resolve().parent.parent / "logs" / "spend.csv"
CAP_USD = {"dev": 25.00, "demo": 20.00}        # D121: dev $25 (was $15); D115: dev counts all rows, demo only its own
PRICE = {                                      # $ per 1M tokens (input, output), checked 2026-11-03
    "qwen/qwen3.5-9b": (0.10, 0.15),           # OpenRouter, DeepInfra host (D39)
    "qwen/qwen3-14b": (0.12, 0.24),
    "qwen/qwen3.5-27b": (0.26, 2.60),
    "moonshotai/kimi-k3": (2.85, 14.25),       # DeepInfra endpoint, checked 2026-11-14 (D121)
    "claude-sonnet-5-5": (2.00, 10.00),        # D43
    "claude-opus-5-5": (4.00, 20.00),
}
COLUMNS = ["timestamp", "path", "model", "budget", "status", "input_tokens", "output_tokens", "cost_usd", "latency_s"]


class CapReached(Exception):
    """The call was refused before it was sent: it could take the month's spend past its budget's cap."""


def month_spend(budget=None):
    """Dollars logged so far in the current UTC calendar month, for one budget's rows or (None) all rows."""
    if not SPEND_LOG.exists():
        return 0.0
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    rows = csv.DictReader(io.StringIO(SPEND_LOG.read_text()))
    return sum(float(r["cost_usd"]) for r in rows
               if r["timestamp"].startswith(month) and budget in (None, r.get("budget")))


def cost(model, input_tokens, output_tokens):
    p_in, p_out = PRICE[model]
    return round((input_tokens * p_in + output_tokens * p_out) / 1e6, 6)


def check(row, request, max_tokens):
    """Raise CapReached, after logging the refusal, unless this paid call fits under its budget's cap.

    The worst case counts the request at two characters per token, an overestimate, plus max_tokens of
    output. A paid model with no price is always refused, so it cannot slip past the cap.
    """
    if row["path"] == "local":
        return
    spent = month_spend("demo" if row["budget"] == "demo" else None)
    cap = CAP_USD[row["budget"]]
    if row["model"] in PRICE:
        worst = cost(row["model"], len(json.dumps(request)) / 2, max_tokens)
        if spent + worst <= cap:
            return
        why = f"this call could cost ${worst:.4f}"
    else:
        why = f"{row['model']} has no price in agent/spend.py"
    log("refused", row)
    raise CapReached(f"{row['budget']} cap ${cap:.2f}: ${spent:.4f} spent this month; {why}")


def log(status, row):
    SPEND_LOG.parent.mkdir(exist_ok=True)
    new = not SPEND_LOG.exists()
    with SPEND_LOG.open("a", newline="") as f:
        writer = csv.DictWriter(f, COLUMNS, extrasaction="ignore", lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow({**row, "status": status, "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")})
