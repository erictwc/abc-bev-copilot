# evals/

Eval cases (`cases.toml`), the runner and scorer (T7), the written pass bar (`BAR.md`, T8,
committed before the first full run and never edited after it) and the judge spot check (T9).

- `cases.toml`: one `[[case]]` per case, read with `tomllib` (D68). The fields are documented at the top of
  the file (D69). Eric writes the first 20 himself (D75); Claude Code drafted E21-E40 and Eric approved each (D78).
- `score.py`: validates the cases and scores a result: numbers exact unless `tolerance_pct` is set (zero to twenty may be words, D76), text
  case-insensitive, HX-7Q2M forbidden everywhere, expected tools called, citations per document with no invented
  ones, and a run stopped by the step cap fails (D70, D71) Since D118 `expect_any` is no longer a code gate: the
  judge weighs it as expected wording, and the scorer only records whether a phrase matched (`wording_matched`).
- `judge.py`, `judge_prompt.md`: the T9 judge, `claude-opus-5-5` on every path (D82). It reads the question, the
  reference `answer`, the notes and the agent's answer (delimited, as data) and returns pass or fail with a reason
  (D83), plus the case's `expect_any` phrases as wording to weigh (D118). It also gives a letter grade A+ to F
  on four points (facts right; the right clarifying question or decline; no invented figure; cited properly) that
  must agree with the verdict: a pass A+ to B-, a fail C+ to F, else the reply is an error (D119). Result files
  carry a `grade` column and a grade-point average on the 4.0 scale (A+ = A = 4.0) beside pass/fail.
  A case passes only when the code checks and the judge both pass it (BAR.md, D84). `make judge RUN=<run>.jsonl`
  judges an earlier run into `<run>_judged.*`, leaving the original files as they were.
- `rescore.py`: `make rescore RUN=<run>.jsonl` re-runs a stored run's code checks on the current cases, keeping
  its judge verdicts (D105). `regrade.py`: `make regrade RUN=<run>.jsonl CASES="..."` re-runs the code checks
  under D118 and asks the judge again for a verdict and grade, with no agent call (T15), into `<run>_graded.*`.
  Neither is the measured result: under `BAR.md` a run stands as run.
- `JUDGE_CHECK.md`: Eric's hand check of 10 judge calls and every disagreement (D85).
- `run.py`: `make evals [EVAL_PATH=claude] [EVAL_MODEL=...] [ONLY=E01,E02]` runs each case through `agent.loop.ask()`
  on the `dev` budget and writes `results/<UTC time>_<path>_<model>.csv`, `.md` and `.jsonl` (D72, D74), judged as it goes (D84). Needs the
  box (`OLLAMA_HOST`) and the Anthropic key for the judge on every path. Results are committed.
- `make evals-check`: offline: validates `cases.toml`, then the scorer, runner, judge, grade and regrade tests with fake results.
