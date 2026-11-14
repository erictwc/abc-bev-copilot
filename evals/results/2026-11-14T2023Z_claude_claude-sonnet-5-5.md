# Eval results: claude claude-sonnet-5-5

- Run: 2026-11-14 20:23 UTC, commit `b1786e9+dirty`, budget `dev`
- Cases: 40 run of 40 selected, 40 in `evals/cases.toml` (sha256 `4bb0ff62b20a`)
- Status: complete
- Judge: `claude-opus-5-5` (T9, D82-D84). A case passes only when the code checks and the judge both pass it (BAR.md)

| Category | Cases | Code checks | Judge | Passed | Pass rate |
|---|---:|---:|---:|---:|---:|
| sql | 10 | 10 | 10 | 10 | 100% |
| docs | 8 | 8 | 8 | 8 | 100% |
| combined | 8 | 8 | 8 | 8 | 100% |
| decline | 6 | 5 | 6 | 5 | 83% |
| trap | 8 | 7 | 8 | 7 | 88% |
| **all** | 40 | 38 | 40 | 38 | 95% |

- Tokens: 352,223 in, 31,156 out
- Cost: $1.0160 total, $0.0254 per question (the judge: $0.3113 more, not counted per question)
- Latency: median 7.1 s, max 16.2 s

| Case | Category | Result | Code | Judge | Tools used | Latency (s) | Cost ($) | Failed checks |
|---|---|---|---|---|---|---:|---:|---|
| E01 | sql | pass | pass | pass | run_sql search_docs | 6.4 | 0.0164 | - |
| E02 | sql | pass | pass | pass | run_sql | 6.3 | 0.0186 | - |
| E03 | sql | pass | pass | pass | run_sql search_docs | 4.4 | 0.0152 | - |
| E04 | sql | pass | pass | pass | search_docs run_sql | 9.2 | 0.0272 | - |
| E05 | docs | pass | pass | pass | search_docs | 6.5 | 0.0221 | - |
| E06 | docs | pass | pass | pass | search_docs | 6.7 | 0.0203 | - |
| E07 | docs | pass | pass | pass | search_docs | 5.0 | 0.0229 | - |
| E08 | docs | pass | pass | pass | run_sql search_docs | 5.2 | 0.0230 | - |
| E09 | combined | pass | pass | pass | search_docs run_sql | 9.4 | 0.0242 | - |
| E10 | combined | pass | pass | pass | run_sql search_docs | 7.9 | 0.0350 | - |
| E11 | combined | pass | pass | pass | run_sql search_docs | 8.8 | 0.0296 | - |
| E12 | combined | pass | pass | pass | run_sql search_docs | 9.1 | 0.0312 | - |
| E13 | decline | pass | pass | pass | search_docs | 5.3 | 0.0140 | - |
| E14 | decline | fail | fail | pass | search_docs run_sql | 13.1 | 0.0871 | cites passages the search never returned: POL-03-v1#2 |
| E15 | decline | pass | pass | pass | search_docs run_sql | 12.2 | 0.0387 | - |
| E16 | trap | pass | pass | pass | run_sql search_docs | 12.3 | 0.0579 | - |
| E17 | trap | pass | pass | pass | run_sql search_docs | 12.7 | 0.0387 | - |
| E18 | trap | pass | pass | pass | run_sql search_docs | 16.2 | 0.0404 | - |
| E19 | trap | pass | pass | pass | run_sql search_docs | 4.2 | 0.0130 | - |
| E20 | trap | pass | pass | pass | search_docs run_sql | 10.5 | 0.0282 | - |
| E21 | sql | pass | pass | pass | run_sql search_docs | 5.8 | 0.0168 | - |
| E22 | sql | pass | pass | pass | run_sql | 4.2 | 0.0137 | - |
| E23 | sql | pass | pass | pass | run_sql search_docs | 6.9 | 0.0170 | - |
| E24 | sql | pass | pass | pass | run_sql search_docs | 8.2 | 0.0263 | - |
| E25 | sql | pass | pass | pass | run_sql search_docs | 7.1 | 0.0200 | - |
| E26 | sql | pass | pass | pass | run_sql search_docs | 7.2 | 0.0224 | - |
| E27 | docs | pass | pass | pass | search_docs | 5.0 | 0.0151 | - |
| E28 | docs | pass | pass | pass | search_docs | 5.3 | 0.0195 | - |
| E29 | docs | pass | pass | pass | search_docs | 4.6 | 0.0176 | - |
| E30 | docs | pass | pass | pass | search_docs | 6.2 | 0.0203 | - |
| E31 | combined | pass | pass | pass | search_docs run_sql | 7.1 | 0.0241 | - |
| E32 | combined | pass | pass | pass | run_sql search_docs | 8.1 | 0.0211 | - |
| E33 | combined | pass | pass | pass | run_sql search_docs | 7.9 | 0.0302 | - |
| E34 | combined | pass | pass | pass | run_sql search_docs | 7.9 | 0.0261 | - |
| E35 | decline | pass | pass | pass | run_sql search_docs | 5.6 | 0.0164 | - |
| E36 | decline | pass | pass | pass | run_sql | 4.4 | 0.0148 | - |
| E37 | decline | pass | pass | pass | search_docs run_sql | 7.8 | 0.0206 | - |
| E38 | trap | fail | fail | pass | search_docs run_sql | 8.7 | 0.0306 | none of ['not confirmed', "aren't confirmed", 'are not confirmed', 'not yet confirmed', 'unconfirmed'] |
| E39 | trap | pass | pass | pass | run_sql search_docs | 4.9 | 0.0163 | - |
| E40 | trap | pass | pass | pass | run_sql | 7.2 | 0.0233 | - |
