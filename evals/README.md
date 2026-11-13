# evals/

Eval cases (`cases.toml`), the runner and scorer (T7), the written pass bar (`BAR.md`, T8,
committed before the first full run and never edited after it) and the judge spot check (T9).

- `cases.toml`: one `[[case]]` per case, read with `tomllib` (D68). The fields are documented at the top of
  the file (D69). Eric writes the first 20 himself (D75); Claude Code drafted E21-E40 and Eric approved each (D78).
- `score.py`: validates the cases and scores a result: numbers exact unless `tolerance_pct` is set (zero to twenty may be words, D76), text
  case-insensitive, HX-7Q2M forbidden everywhere, expected tools called, citations per document with no invented
  ones, and a run stopped by the step cap fails (D70, D71). The judge column reads `pending` until T9.
- `run.py`: `make evals [EVAL_PATH=claude] [EVAL_MODEL=...] [ONLY=E01,E02]` runs each case through `agent.loop.ask()`
  on the `dev` budget and writes `results/<UTC time>_<path>_<model>.csv`, `.md` and `.jsonl` (D72, D74). Needs the
  box (`OLLAMA_HOST`) and, on paid paths, the key. Results are committed.
- `make evals-check`: offline: validates `cases.toml`, then the scorer and runner tests with fake results.
