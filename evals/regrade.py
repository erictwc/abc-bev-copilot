"""Offline regrade (T15, D118, D119): python -m evals.regrade evals/results/<run>.jsonl [--cases ...]

Takes a stored run's answers and, without calling the agent, re-runs the code checks under the current rules
(expect_any is wording the judge weighs, not a code gate) and asks the judge again with the grading prompt, so
each case gets a verdict and a letter grade A+ to F. Judge cost only. Writes <run>_graded.{csv,md,jsonl} next
to the run and leaves the run's own files untouched. A regrade is a separate number, never the measured result:
under BAR.md the measured run stands as run.
"""
import argparse, hashlib, json, sys
from pathlib import Path

from agent import spend
from evals import judge, run, score


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("jsonl", type=Path, help="a run's .jsonl in evals/results/")
    p.add_argument("--cases", type=Path, nargs="+", default=[score.CASES],
                   help="case files the run used (T13: evals/cases.toml evals/holdout.toml)")
    a = p.parse_args(argv)
    cases = {c["id"]: c for f in a.cases for c in score.load(f)}
    lines = [json.loads(x) for x in a.jsonl.read_text().splitlines() if x.strip()]
    if missing := [x["id"] for x in lines if x["id"] not in cases]:
        sys.exit(f"no case with id {', '.join(missing)} in {' + '.join(f.name for f in a.cases)}")
    stem = a.jsonl.with_suffix("")
    out = stem.with_name(stem.name + "_graded")
    meta = judge.meta_from(Path(f"{stem}.md"), a.jsonl, lines)
    old_sha = meta["cases_sha"]
    shown = lambda f: str(f.resolve().relative_to(score.ROOT)) if f.resolve().is_relative_to(score.ROOT) else f.name
    meta.update(judged_from=None, status="complete", cases="` + `".join(shown(f) for f in a.cases),
                cases_sha=" + ".join(hashlib.sha256(f.read_bytes()).hexdigest()[:12] for f in a.cases))
    rows, changed, measured = [], [], 0
    with open(f"{out}.jsonl", "w") as fj:
        for x in lines:
            case, r = cases[x["id"]], x["result"]
            s = score.score(case, r)
            try:
                j = judge.judge(case, r)
            except spend.CapReached:
                meta["status"] = "incomplete: the spend cap stopped the regrade"
                break
            rows.append(run.row(case, r, s, j))
            was = x["score"]["pass"] and x["judge"]["verdict"] == "pass"
            measured += was
            if was != (rows[-1]["pass"] == "pass"):
                changed.append(f"{x['id']} {'pass -> fail' if was else 'fail -> pass'}")
            fj.write(json.dumps({**x, "score": s, "judge": j, "score_as_run": x["score"], "judge_as_run": x["judge"]},
                                default=str) + "\n")
            print(f"{rows[-1]['pass'].upper()} {x['id']}: code {rows[-1]['code_pass']}, judge {j['verdict']} "
                  f"{j['grade'] or '-'} -- {j['reason']}")
    run.write_csv(f"{out}.csv", rows)
    md = run.summary(rows, meta).split("\n")
    md[0] += " (regraded offline, D118)"
    prompt_sha = hashlib.sha256(judge.PROMPT.encode()).hexdigest()[:12]
    notes = [f"- Regraded offline from `{a.jsonl.name}` (cases as run: sha256 `{old_sha}`): the stored answers, no "
             "agent call. Code checks re-run under the D118 rules (expect_any is wording the judge weighs, not a gate); "
             f"the judge asked again with the grading prompt (`evals/judge_prompt.md` sha256 `{prompt_sha}`). "
             "Not the measured result (BAR.md)",
             f"- Measured as run: {measured}/{len(rows)} pass. Regraded: {sum(x['pass'] == 'pass' for x in rows)}"
             f"/{len(rows)}. Changed: {', '.join(changed) or 'none'}"]
    at = next(i for i, s in enumerate(md) if s.startswith("- Status:")) + 1
    md[at:at] = notes
    Path(f"{out}.md").write_text("\n".join(md))
    g, n = judge.gpa(x["grade"] for x in rows)
    print(f"{sum(x['pass'] == 'pass' for x in rows)}/{len(rows)} pass regraded ({measured} as measured); "
          f"grade points {'-' if g is None else f'{g:.2f}'} over {n} graded; judge cost "
          f"${sum(x['judge_cost_usd'] for x in rows):.4f}; {meta['status']}\nwrote {out.name}.{{csv,md,jsonl}}")
    return 0 if meta["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
