# Eval results: claude claude-sonnet-5-5 (rescored offline)

- Run: 2026-11-14 20:31 UTC, commit `09e2148`, budget `dev`
- Cases: 50 run of 50 selected, 50 in `evals/cases.toml` (sha256 `bb0ddb451fe1 + c63da6785847`)
- Status: complete
- Rescored offline from `2026-11-14T2031Z_claude_claude-sonnet-5-5.jsonl` (cases as run: sha256 `4bb0ff62b20a + c63da6785847`): code checks re-run on the current case file, judge verdicts as stored, no model called. Not the measured result (BAR.md)
- Code checks changed: E19 code fail -> pass
- Judge: `claude-opus-5-5` (T9, D82-D84). A case passes only when the code checks and the judge both pass it (BAR.md)

| Category | Cases | Code checks | Judge | Passed | Pass rate |
|---|---:|---:|---:|---:|---:|
| sql | 12 | 12 | 12 | 12 | 100% |
| docs | 10 | 10 | 9 | 9 | 90% |
| combined | 10 | 9 | 10 | 9 | 90% |
| decline | 8 | 8 | 6 | 6 | 75% |
| trap | 10 | 9 | 10 | 9 | 90% |
| **all** | 50 | 48 | 47 | 45 | 90% |

- Tokens: 400,086 in, 38,442 out
- Cost: $1.1846 total, $0.0237 per question (the judge: $0.3931 more, not counted per question)
- Latency: median 6.9 s, max 37.9 s

| Case | Category | Result | Code | Judge | Tools used | Latency (s) | Cost ($) | Failed checks |
|---|---|---|---|---|---|---:|---:|---|
| E01 | sql | pass | pass | pass | run_sql search_docs | 5.4 | 0.0153 | - |
| E02 | sql | pass | pass | pass | run_sql | 6.6 | 0.0187 | - |
| E03 | sql | pass | pass | pass | run_sql search_docs | 5.1 | 0.0160 | - |
| E04 | sql | pass | pass | pass | search_docs run_sql | 8.5 | 0.0274 | - |
| E05 | docs | pass | pass | pass | search_docs | 6.5 | 0.0208 | - |
| E06 | docs | pass | pass | pass | search_docs | 5.9 | 0.0200 | - |
| E07 | docs | pass | pass | pass | search_docs | 5.0 | 0.0236 | - |
| E08 | docs | pass | pass | pass | run_sql search_docs | 5.8 | 0.0237 | - |
| E09 | combined | pass | pass | pass | search_docs run_sql | 8.4 | 0.0238 | - |
| E10 | combined | pass | pass | pass | run_sql search_docs | 8.5 | 0.0352 | - |
| E11 | combined | pass | pass | pass | run_sql search_docs | 8.4 | 0.0207 | - |
| E12 | combined | pass | pass | pass | run_sql search_docs | 8.6 | 0.0308 | - |
| E13 | decline | pass | pass | pass | search_docs | 5.0 | 0.0136 | - |
| E14 | decline | fail | pass | fail | search_docs run_sql | 15.0 | 0.0706 | judge fail: The answer correctly declines ROI and payback, but it then offers a substitute realized-lift figure (−6.9% vs the 37% plan) and concludes there is no sign of a sales increase, using all-distributor depletion totals that the reference says cannot establish this chain's promo results. |
| E15 | decline | pass | pass | pass | run_sql search_docs | 7.3 | 0.0175 | - |
| E16 | trap | pass | pass | pass | run_sql search_docs | 10.1 | 0.0391 | - |
| E17 | trap | pass | pass | pass | run_sql search_docs | 37.9 | 0.0385 | - |
| E18 | trap | pass | pass | pass | run_sql search_docs | 12.8 | 0.0395 | - |
| E19 | trap | pass | pass | pass | run_sql search_docs | 4.5 | 0.0130 | - |
| E20 | trap | pass | pass | pass | search_docs run_sql | 7.0 | 0.0193 | - |
| E21 | sql | pass | pass | pass | run_sql search_docs | 5.9 | 0.0227 | - |
| E22 | sql | pass | pass | pass | run_sql | 4.1 | 0.0140 | - |
| E23 | sql | pass | pass | pass | run_sql search_docs | 6.6 | 0.0172 | - |
| E24 | sql | pass | pass | pass | run_sql search_docs | 8.6 | 0.0266 | - |
| E25 | sql | pass | pass | pass | run_sql search_docs | 5.5 | 0.0186 | - |
| E26 | sql | pass | pass | pass | run_sql search_docs | 7.5 | 0.0226 | - |
| E27 | docs | pass | pass | pass | search_docs | 5.6 | 0.0161 | - |
| E28 | docs | pass | pass | pass | search_docs | 5.8 | 0.0206 | - |
| E29 | docs | pass | pass | pass | search_docs | 4.3 | 0.0175 | - |
| E30 | docs | pass | pass | pass | search_docs | 7.0 | 0.0215 | - |
| E31 | combined | pass | pass | pass | search_docs run_sql | 7.2 | 0.0240 | - |
| E32 | combined | pass | pass | pass | run_sql search_docs | 9.8 | 0.0214 | - |
| E33 | combined | pass | pass | pass | run_sql search_docs | 8.5 | 0.0305 | - |
| E34 | combined | pass | pass | pass | run_sql search_docs | 8.3 | 0.0262 | - |
| E35 | decline | pass | pass | pass | run_sql search_docs | 5.4 | 0.0167 | - |
| E36 | decline | fail | pass | fail | run_sql | 4.7 | 0.0149 | judge fail: The answer states the 2023 figure is 0 cases, which the notes forbid because data before November 2024 does not exist, and its later hedge does not undo that claim. |
| E37 | decline | pass | pass | pass | search_docs run_sql | 7.2 | 0.0255 | - |
| E38 | trap | fail | fail | pass | search_docs run_sql | 8.7 | 0.0294 | none of ['not confirmed', "aren't confirmed", 'are not confirmed', 'not yet confirmed', 'unconfirmed'] |
| E39 | trap | pass | pass | pass | run_sql search_docs | 4.8 | 0.0153 | - |
| E40 | trap | pass | pass | pass | run_sql search_docs | 6.9 | 0.0249 | - |
| E41 | sql | pass | pass | pass | run_sql search_docs | 7.2 | 0.0214 | - |
| E42 | sql | pass | pass | pass | run_sql | 5.5 | 0.0172 | - |
| E43 | docs | fail | pass | fail | search_docs | 5.8 | 0.0188 | judge fail: The answer correctly names Supply Planning as owner, the Portfolio Manager as helper, the Product VP at 24 hours and ownership after that. It then says the 24-hour step is likely the Product VP and Commercial VP together, which contradicts the note that the Commercial VP is not the default escalation destination. |
| E44 | docs | pass | pass | pass | search_docs | 6.9 | 0.0236 | - |
| E45 | combined | pass | pass | pass | run_sql search_docs | 5.9 | 0.0179 | - |
| E46 | combined | fail | fail | pass | search_docs run_sql | 8.2 | 0.0242 | cites passages the search never returned: POL-02-v1#2; did not cite POL-02-v1 |
| E47 | decline | pass | pass | pass | search_docs run_sql | 10.1 | 0.0399 | - |
| E48 | decline | pass | pass | pass | run_sql search_docs | 7.7 | 0.0273 | - |
| E49 | trap | pass | pass | pass | run_sql search_docs | 6.6 | 0.0184 | - |
| E50 | trap | pass | pass | pass | run_sql search_docs | 5.5 | 0.0225 | - |
