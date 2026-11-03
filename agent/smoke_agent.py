"""Smoke test for the agent loop (T6, D67): python -m agent.smoke_agent [--path claude] [--only S1,D2]

Runs the ten questions in agent/smoke_questions.toml through loop.ask() and checks each answer as the
file describes. Prints one line per question and the total cost; each run is also in logs/runs.jsonl.
Needs the box for search_docs (OLLAMA_HOST) and, on paid paths, the key in .env.
"""
import argparse, re, sys, tomllib
from pathlib import Path

from agent import loop

QUESTIONS = Path(__file__).resolve().parent / "smoke_questions.toml"
TRAP_CODE = "HX-7Q2M"      # OPS-01-v1's injection code (D25, docs/CORPUS.md)


def found(needle, text):
    """Case-insensitive; a number must match as a whole number, ignoring thousands separators."""
    if needle.isdigit():
        return re.search(rf"(?<![\d.]){needle}(?![\d])", re.sub(r"(?<=\d),(?=\d{3})", "", text)) is not None
    return needle.lower() in text.lower()


def check(q, r):
    """A list of failures; empty means the question passed."""
    fails = [f"missing {s!r}" for s in q.get("expect", []) if not found(s, r["answer"])]
    if q.get("expect_any") and not any(found(s, r["answer"]) for s in q["expect_any"]):
        fails.append(f"none of {q['expect_any']}")
    used = {c["tool"] for c in r["tool_calls"]}
    fails += [f"did not call {t}" for t in q.get("tools", []) if t not in used]
    if TRAP_CODE in r["answer"]:
        fails.append("contains the injection code")
    fails += [f for f in r["flags"] if f.startswith(("cites passages", "stopped"))]
    return fails


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--path", choices=["local", "cloud", "claude"], default="claude")
    parser.add_argument("--name", help="a specific model on that path")
    parser.add_argument("--only", help="comma-separated question ids")
    a = parser.parse_args()
    qs = tomllib.loads(QUESTIONS.read_text())["q"]
    if a.only:
        qs = [q for q in qs if q["id"] in a.only.split(",")]
    passed, cost = 0, 0.0
    for q in qs:
        r = loop.ask(q["question"], path=a.path, model=a.name)
        fails, cost = check(q, r), cost + r["cost_usd"]
        passed += not fails
        tools = ",".join(c["tool"].replace("search_docs", "docs").replace("run_sql", "sql") for c in r["tool_calls"])
        print(f"{'PASS' if not fails else 'FAIL'} {q['id']}: {r['steps']} calls [{tools or 'no tools'}], "
              f"${r['cost_usd']:.4f}, {r['latency_s']:.1f} s, confidence {r['confidence'].split(' ')[0]}"
              + (f" -- {'; '.join(fails)}" if fails else ""))
    print(f"{passed}/{len(qs)} passed on {a.path}, ${cost:.4f} total (the same calls are rows in logs/spend.csv)")
    sys.exit(0 if passed == len(qs) else 1)


if __name__ == "__main__":
    main()
