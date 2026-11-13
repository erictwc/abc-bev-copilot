"""The eval runner (T7, D72-D74): python -m evals.run [--path claude] [--name MODEL] [--only E01,E02]

Runs each case in evals/cases.toml through agent.loop.ask() one at a time on the "dev" budget, scores it
(evals/score.py), asks the judge (evals/judge.py, T9) and writes three files to evals/results/<UTC time>_<path>_<model>:
  .csv    one row per case: pass, code checks, judge verdict, failed checks, tools, citation, latency, tokens, cost
  .md     pass rate by category, totals, cost per question, the commit and case file it ran on
  .jsonl  each case's full answer, evidence and judge reply, for auditing a failure
A case passes only when the code checks and the judge both pass it (BAR.md, D84). A failed model or judge call
is a failed case and the run goes on; a spend-cap refusal of either stops the run and the files
are marked incomplete. Needs the box for search_docs (OLLAMA_HOST) and, on paid paths, the key in .env.
"""
import argparse, csv, hashlib, json, statistics, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

from agent import adapter, loop, spend
from evals import judge, score

RESULTS = score.ROOT / "evals" / "results"
COLUMNS = ["id", "category", "author", "pass", "code_pass", "judge", "judge_reason", "failed", "tools_expected",
           "tools_used", "tools_ok", "citation_ok", "stopped", "steps", "confidence", "latency_s", "input_tokens",
           "output_tokens", "cost_usd", "judge_cost_usd"]
NOT_JUDGED = {"verdict": "error", "reason": "not judged: the spend cap stopped the run", "model": judge.MODEL,
              "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}


def commit():
    """Short commit hash, with +dirty when the working tree has changes."""
    git = lambda *a: subprocess.run(["git", *a], cwd=score.ROOT, capture_output=True, text=True).stdout.strip()
    return (git("rev-parse", "--short", "HEAD") or "unknown") + ("+dirty" if git("status", "--porcelain") else "")


def row(case, r, s, j):
    """One CSV row. s is the code-scored result, j the judge's; the case passes only if both do (D84)."""
    failed = s["failed"] + ([] if j["verdict"] == "pass" else [f"judge {j['verdict']}: {j['reason']}"])
    return {"id": case["id"], "category": case["category"], "author": case["author"],
            "pass": "pass" if s["pass"] and j["verdict"] == "pass" else "fail",
            "code_pass": "pass" if s["pass"] else "fail", "judge": j["verdict"], "judge_reason": j["reason"],
            "failed": "; ".join(failed),
            "tools_expected": " ".join(case.get("tools", [])), "tools_used": " ".join(s["tools_used"]),
            "tools_ok": s["tools_ok"], "citation_ok": s["citation_ok"],
            "stopped": r["stopped"], "steps": r["steps"], "confidence": r["confidence"].split(" ")[0],
            "latency_s": r["latency_s"], "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
            "cost_usd": r["cost_usd"], "judge_cost_usd": j["cost_usd"]}


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def summary(rows, meta):
    """The .md file: run details, pass rate by category, totals, then one line per case."""
    def rate(rs):
        n = lambda k, v="pass": sum(x[k] == v for x in rs)
        return f"| {n('code_pass')} | {n('judge')} | {n('pass')} | {n('pass') / len(rs):.0%} |"
    out = [f"# Eval results: {meta['path']} {meta['model']}", "",
           f"- Run: {meta['started']} UTC, commit `{meta['commit']}`, budget `dev`",
           f"- Cases: {len(rows)} run of {meta['selected']} selected, {meta['in_file']} in `{meta['cases']}` "
           f"(sha256 `{meta['cases_sha']}`)",
           f"- Status: {meta['status']}",
           *([f"- Judged afterwards from `{meta['judged_from']}`; the code checks are as scored in that run"]
             if meta.get("judged_from") else []),
           f"- Judge: `{judge.MODEL}` (T9, D82-D84). A case passes only when the code checks and the judge "
           "both pass it (BAR.md)", "",
           "| Category | Cases | Code checks | Judge | Passed | Pass rate |", "|---|---:|---:|---:|---:|---:|"]
    for k in score.CATEGORIES:
        rs = [x for x in rows if x["category"] == k]
        if rs:
            out.append(f"| {k} | {len(rs)} {rate(rs)}")
    out.append(f"| **all** | {len(rows)} {rate(rows)}")
    if rows:
        cost, lat = sum(x["cost_usd"] for x in rows), [x["latency_s"] for x in rows]
        out += ["", f"- Tokens: {sum(x['input_tokens'] for x in rows):,} in, {sum(x['output_tokens'] for x in rows):,} out",
                f"- Cost: ${cost:.4f} total, ${cost / len(rows):.4f} per question "
                f"(the judge: ${sum(x['judge_cost_usd'] for x in rows):.4f} more, not counted per question)",
                f"- Latency: median {statistics.median(lat):.1f} s, max {max(lat):.1f} s"]
    out += ["", "| Case | Category | Result | Code | Judge | Tools used | Latency (s) | Cost ($) | Failed checks |",
            "|---|---|---|---|---|---|---:|---:|---|"]
    out += [f"| {x['id']} | {x['category']} | {x['pass']} | {x['code_pass']} | {x['judge']} | {x['tools_used'] or '-'} | "
            f"{x['latency_s']:.1f} | {x['cost_usd']:.4f} | {x['failed'].replace('|', '/') or '-'} |" for x in rows]
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--path", choices=["local", "cloud", "claude"], default="claude")
    p.add_argument("--name", help="a specific model on that path (default: the adapter's)")
    p.add_argument("--only", help="comma-separated case ids")
    p.add_argument("--cases", type=Path, default=score.CASES, help=argparse.SUPPRESS)   # for development runs
    p.add_argument("--out", type=Path, default=RESULTS, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    try:
        cases = score.load(a.cases)
    except ValueError as e:
        sys.exit(str(e))
    in_file = len(cases)
    if a.only:
        wanted = a.only.split(",")
        if unknown := [i for i in wanted if i not in {c["id"] for c in cases}]:
            sys.exit(f"no case with id {', '.join(unknown)}")
        cases = [c for c in cases if c["id"] in wanted]
    if not cases:
        sys.exit(f"no cases in {a.cases} yet")

    model = a.name or adapter.DEFAULT[a.path]
    if model == judge.MODEL:
        sys.exit(f"{model} is the judge, so it cannot be the model under test (D6, D82)")
    started = datetime.now(timezone.utc)
    stem = a.out / f"{started:%Y-%m-%dT%H%MZ}_{a.path}_{model.replace('/', '-').replace(':', '-')}"
    a.out.mkdir(parents=True, exist_ok=True)
    try:
        cases_name = str(a.cases.resolve().relative_to(score.ROOT))
    except ValueError:
        cases_name = a.cases.name
    meta = {"path": a.path, "model": model, "started": f"{started:%Y-%m-%d %H:%M}", "commit": commit(),
            "cases": cases_name, "cases_sha": hashlib.sha256(a.cases.read_bytes()).hexdigest()[:12],
            "in_file": in_file, "selected": len(cases), "status": "incomplete: interrupted"}
    rows = []
    with open(f"{stem}.csv", "w", newline="") as fc, open(f"{stem}.jsonl", "w") as fj:
        w = csv.DictWriter(fc, COLUMNS, lineterminator="\n")
        w.writeheader()
        try:
            for case in cases:
                r = loop.ask(case["question"], path=a.path, model=a.name, budget="dev")
                s = score.score(case, r)
                capped = r["stopped"] == "spend_cap"
                j = NOT_JUDGED
                if not capped:
                    try:
                        j = judge.judge(case, r)
                    except spend.CapReached:
                        capped, j = True, {**NOT_JUDGED, "reason": "the spend cap refused the judge call"}
                rows.append(row(case, r, s, j))
                w.writerow(rows[-1])
                fj.write(json.dumps({"id": case["id"], "score": s, "result": r, "judge": j}, default=str) + "\n")
                fc.flush(), fj.flush()
                print(f"{rows[-1]['pass'].upper()} {case['id']} [{case['category']}]: {r['steps']} calls "
                      f"[{rows[-1]['tools_used'] or 'no tools'}], ${r['cost_usd']:.4f}, {r['latency_s']:.1f} s, "
                      f"judge {j['verdict']}" + (f" -- {rows[-1]['failed']}" if rows[-1]["failed"] else ""))
                if capped:
                    meta["status"] = "incomplete: the spend cap stopped the run"
                    break
            else:
                meta["status"] = "complete"
        finally:
            Path(f"{stem}.md").write_text(summary(rows, meta))
    passed = sum(x["pass"] == "pass" for x in rows)
    print(f"{passed}/{len(rows)} passed on {a.path} {model}, ${sum(x['cost_usd'] for x in rows):.4f} total, "
          f"{meta['status']}\nwrote {stem.relative_to(score.ROOT) if stem.is_relative_to(score.ROOT) else stem}"
          f".{{csv,md,jsonl}}")
    return 0 if meta["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
