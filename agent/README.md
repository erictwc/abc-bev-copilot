# agent/

The model adapter (`adapter.py`, under 100 lines, ticket T4), the two tools `run_sql` and
`search_docs` (T5), and the agent loop (T6).

- `adapter.py`: `call(path, messages, tools)` for `local`, `cloud` and `claude` (D39-D43).
- `spend.py`: the spend log (`logs/spend.csv`, gitignored) and the monthly cap: development calls stop
  at $15, demo calls at $20, counting the worst case of the next call (D41, D44-D46).
- `make test-adapter`: offline tests of the cap, the log, retries and message handling.
- `make smoke PATHS="cloud claude"`: one tool-call round trip per path. Needs the keys in `.env`.
- `tools.py`: `run_sql(query)`, read-only over the six tables, one SELECT, allow-listed tables, at most 200 rows,
  10 s timeout; `search_docs(query, k)`, top-k chunks above the score threshold, cited `<DOC-ID>#<n>`. Every call
  is logged to `logs/tools.csv` (D47-D56). Retrieval settings are in `config.toml`; the SQL limits are in code.
- `index.py`: `make db` builds `data/abc.duckdb` from the CSVs, `make index` builds `data/docs.duckdb` with embeddings
  from `qwen3-embedding:0.6b` on the box. Both are gitignored.
- `make test-tools`: offline tests of the SQL guard rails, chunking and search. `make test-retrieval`: five
  hand-picked questions against the box.
