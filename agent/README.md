# agent/

The model adapter (`adapter.py`, under 100 lines, ticket T4), the two tools `run_sql` and
`search_docs` (T5), and the agent loop (T6).

- `adapter.py`: `call(path, messages, tools)` for `local`, `cloud` and `claude` (D39-D43).
- `spend.py`: the spend log (`logs/spend.csv`, gitignored) and the monthly cap: development calls stop
  at $15, demo calls at $20, counting the worst case of the next call (D41, D44-D46).
- `make test-adapter`: offline tests of the cap, the log, retries and message handling.
- `make smoke PATHS="cloud claude"`: one tool-call round trip per path. Needs the keys in `.env`.
