"""Offline rescore (T12, D105): python -m evals.rescore evals/results/<run>.jsonl

Re-runs the code checks of a stored run against the current evals/cases.toml and keeps the judge verdicts the
run stored. No model is called, so it needs neither the box nor a key. Writes <run>_rescored.{csv,md,jsonl}
next to the run and leaves the run's own files untouched. A rescore is a separate number on corrected cases,
never the measured result: under BAR.md the measured run stands as run.
"""
import argparse, hashlib, json, sys
from pathlib import Path

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
    out = stem.with_name(stem.name + "_rescored")
    meta = judge.meta_from(Path(f"{stem}.md"), a.jsonl, lines)
    old_sha = meta["cases_sha"]
    meta.update(judged_from=None, cases_sha=" + ".join(hashlib.sha256(f.read_bytes()).hexdigest()[:12] for f in a.cases))
    rows, changed = [], []
    with open(f"{out}.jsonl", "w") as fj:
        for x in lines:
            case, r, j = cases[x["id"]], x["result"], x["judge"]      # the judge verdict as stored
            s = score.score(case, r)
            rows.append(run.row(case, r, s, j))
            if s["pass"] != x["score"]["pass"]:
                changed.append(f"{x['id']} code {'fail -> pass' if s['pass'] else 'pass -> fail'}")
            fj.write(json.dumps({**x, "score": s, "score_as_run": x["score"]}, default=str) + "\n")
    run.write_csv(f"{out}.csv", rows)
    md = run.summary(rows, meta).split("\n")
    md[0] += " (rescored offline)"
    note = (f"- Rescored offline from `{a.jsonl.name}` (cases as run: sha256 `{old_sha}`): code checks re-run on the "
            "current case file, judge verdicts as stored, no model called. Not the measured result (BAR.md)")
    md.insert(next(i for i, s in enumerate(md) if s.startswith("- Status:")) + 1, note)
    md.insert(md.index(note) + 1, f"- Code checks changed: {', '.join(changed) or 'none'}")
    Path(f"{out}.md").write_text("\n".join(md))
    passed = sum(x["pass"] == "pass" for x in rows)
    print(f"{passed}/{len(rows)} pass on the current cases; {', '.join(changed) or 'no code checks changed'}\n"
          f"wrote {out.name}.{{csv,md,jsonl}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
