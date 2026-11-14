"""The judge (T9, D82-D86): python -m evals.judge evals/results/<run>.jsonl

judge() asks claude-opus-5-5, a model that differs from every model under test (D6, D82), whether the agent's
answer agrees with the case's reference `answer`. It reads the question, the reference answer, the case notes,
the case's `expect_any` phrases as wording to weigh (D118) and the agent's answer, delimited, with the agent's
answer marked as data (D83). It returns pass, fail or error, a letter grade A+ to F that agrees with the verdict
(D118, D119), and a one-sentence reason. A case passes only when the code checks and the judge both pass it
(BAR.md, D84).

evals/run.py calls judge() on every case. Run as a module, this file judges an earlier run's .jsonl and writes
<run>_judged.{csv,md,jsonl} next to it, leaving the original files as they were (D84).
"""
import argparse, json, re, sys
from pathlib import Path

from agent import adapter, spend
from evals import score

PATH, MODEL = "claude", "claude-opus-5-5"
PROMPT = (Path(__file__).resolve().parent / "judge_prompt.md").read_text()
MAX_TOKENS = 2000      # Opus thinks first and the thinking counts here; 300 cut replies off (D86)
TAGS = ("question", "reference_answer", "notes", "expected_wording", "agent_answer")
PASS_GRADES = ("A+", "A", "A-", "B+", "B", "B-")
FAIL_GRADES = ("C+", "C", "C-", "D", "F")
POINTS = {"A+": 4.0, "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,        # D119: the usual 4.0 scale
          "C+": 2.3, "C": 2.0, "C-": 1.7, "D": 1.0, "F": 0.0}
TAG = re.compile(r"<(/?)(" + "|".join(TAGS) + r")>", re.I)


def fence(name, text):
    """Text inside <name> tags; any of our tags inside it is defused, so the agent cannot close its own block."""
    return f"<{name}>\n{TAG.sub(lambda m: f'&lt;{m[1]}{m[2]}&gt;', text.strip())}\n</{name}>"


def messages(case, answer):
    parts = [fence("question", case["question"]), fence("reference_answer", case["answer"]),
             fence("notes", case.get("notes") or "none")]
    if case.get("expect_any"):
        parts.append(fence("expected_wording", "\n".join(case["expect_any"])))
    parts.append(fence("agent_answer", answer or "(empty)"))
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": "\n\n".join(parts)}]


def parse(text):
    """(verdict, grade, reason) from the judge's reply. Anything but one clean object whose grade agrees with its
    verdict (a pass A+ to B-, a fail C+ to F) is an error with grade "" (D119)."""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        out = json.loads(m[0]) if m else None
    except json.JSONDecodeError:
        out = None
    if not isinstance(out, dict) or out.get("verdict") not in ("pass", "fail") or not isinstance(out.get("reason"), str):
        return "error", "", f"unreadable judge reply: {text.strip()[:200]!r}"
    if out.get("grade") not in (PASS_GRADES if out["verdict"] == "pass" else FAIL_GRADES):
        return "error", "", f"judge grade {out.get('grade')!r} does not fit verdict {out['verdict']}"
    return out["verdict"], out["grade"], " ".join(out["reason"].split())


def judge(case, r):
    """{verdict, grade, reason, model, input_tokens, output_tokens, cost_usd} for one case's result.

    Raises ValueError if the model under test is the judge, and spend.CapReached if the cap refuses the call.
    Any other failure is verdict "error", which fails the case (D84).
    """
    if r.get("model") == MODEL:
        raise ValueError(f"{MODEL} cannot judge its own answers (D6)")
    out = {"verdict": "error", "grade": "", "reason": "", "model": MODEL, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}
    if r.get("question") not in (None, case["question"]):
        return {**out, "reason": "the case's question changed after this run"}
    try:
        reply = adapter.call(PATH, messages(case, r["answer"]), model=MODEL, max_tokens=MAX_TOKENS, budget="dev")
    except spend.CapReached:
        raise
    except Exception as e:
        return {**out, "reason": f"judge call failed: {str(e)[:200]}"}
    verdict, grade, reason = parse(reply["text"])
    if verdict == "error" and reply.get("stop") == "max_tokens":
        reason = f"judge reply cut off at max_tokens={MAX_TOKENS}"
    return {**out, "verdict": verdict, "grade": grade, "reason": reason, "input_tokens": reply["input_tokens"],
            "output_tokens": reply["output_tokens"], "cost_usd": reply["cost_usd"]}


def gpa(grades):
    """The mean grade points of the graded answers, and how many there were; ungraded ("") are left out."""
    pts = [POINTS[g] for g in grades if g in POINTS]
    return (sum(pts) / len(pts) if pts else None), len(pts)


def meta_from(md, jsonl, rows):
    """The original run's header facts, read back from its .md summary."""
    text = md.read_text() if md.exists() else ""
    grab = lambda pat, default="unknown": (m[1] if (m := re.search(pat, text)) else default)
    first = rows[0]["result"] if rows else {}
    return {"path": first.get("path", "unknown"), "model": first.get("model", "unknown"),
            "started": grab(r"Run: (.+?) UTC"), "commit": grab(r"commit `([^`]+)`"),
            "cases": grab(r"in `([^`]+)`"), "cases_sha": grab(r"sha256 `([^`]+)`"),
            "in_file": grab(r"selected, (\d+) in"), "selected": grab(r"run of (\d+) selected", len(rows)),
            "status": grab(r"Status: (.+)"), "judged_from": jsonl.name}


def main(argv=None):
    from evals import run          # run imports this module, so import it here
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("jsonl", type=Path, help="a run's .jsonl in evals/results/")
    a = p.parse_args(argv)
    cases = {c["id"]: c for c in score.load()}
    lines = [json.loads(x) for x in a.jsonl.read_text().splitlines() if x.strip()]
    if missing := [x["id"] for x in lines if x["id"] not in cases]:
        sys.exit(f"no case with id {', '.join(missing)} in {score.CASES.name}")
    stem = a.jsonl.with_suffix("")
    out = stem.with_name(stem.name + "_judged")
    meta = meta_from(Path(f"{stem}.md"), a.jsonl, lines)      # not with_suffix: "qwen3.5-9b" has a dot
    rows = []
    with open(f"{out}.jsonl", "w") as fj:
        for x in lines:
            case, r, s = cases[x["id"]], x["result"], x["score"]      # the code checks as they were scored then
            try:
                j = judge(case, r)
            except spend.CapReached:
                meta["status"] = "incomplete: the spend cap stopped the judging"
                break
            rows.append(run.row(case, r, s, j))
            fj.write(json.dumps({**x, "judge": j}, default=str) + "\n")
            print(f"{rows[-1]['pass'].upper()} {x['id']}: code {rows[-1]['code_pass']}, judge {j['verdict']} -- {j['reason']}")
    run.write_csv(f"{out}.csv", rows)
    Path(f"{out}.md").write_text(run.summary(rows, meta))
    passed = sum(x["pass"] == "pass" for x in rows)
    print(f"{passed}/{len(rows)} pass on code checks and judge; judge cost "
          f"${sum(x['judge_cost_usd'] for x in rows):.4f}\nwrote {out.name}.{{csv,md,jsonl}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
