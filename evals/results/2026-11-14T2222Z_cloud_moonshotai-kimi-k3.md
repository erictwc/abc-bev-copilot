# Eval results: cloud moonshotai/kimi-k3

- Run: 2026-11-14 22:22 UTC, commit `c2be714`, budget `dev`
- Cases: 50 run of 50 selected, 50 in `evals/cases.toml` + `evals/holdout.toml` (sha256 `112f11ac4d25 + c63da6785847`)
- Status: complete
- Judge: `claude-opus-5-5` (T9, D82-D84). A case passes only when the code checks and the judge both pass it (BAR.md). Grade points: the judge's letter grade on the 4.0 scale, A+ = 4.0 (D118, D119)

| Category | Cases | Code checks | Judge | Passed | Pass rate | Grade points |
|---|---:|---:|---:|---:|---:|---:|
| sql | 12 | 12 | 12 | 12 | 100% | 3.93 |
| docs | 10 | 10 | 9 | 9 | 90% | 3.74 |
| combined | 10 | 8 | 10 | 8 | 80% | 3.90 |
| decline | 8 | 7 | 7 | 7 | 88% | 3.38 |
| trap | 10 | 8 | 8 | 8 | 80% | 3.36 |
| **all** | 50 | 45 | 46 | 44 | 88% | 3.68 |

- Tokens: 345,145 in, 61,723 out
- Cost: $1.8632 total, $0.0373 per question (the judge: $0.5252 more, not counted per question)
- Latency: median 7.6 s, max 40.9 s

| Case | Category | Result | Code | Judge | Grade | Tools used | Latency (s) | Cost ($) | Failed checks |
|---|---|---|---|---|---|---|---:|---:|---|
| E01 | sql | pass | pass | pass | A | run_sql search_docs | 12.2 | 0.0241 | - |
| E02 | sql | pass | pass | pass | A+ | run_sql | 3.7 | 0.0167 | - |
| E03 | sql | pass | pass | pass | A | run_sql | 14.3 | 0.0461 | - |
| E04 | sql | pass | pass | pass | A+ | run_sql | 3.3 | 0.0148 | - |
| E05 | docs | pass | pass | pass | A- | search_docs | 5.2 | 0.0179 | - |
| E06 | docs | pass | pass | pass | A | search_docs | 19.8 | 0.0858 | - |
| E07 | docs | pass | pass | pass | A | search_docs | 4.2 | 0.0173 | - |
| E08 | docs | pass | pass | pass | A+ | run_sql search_docs | 6.3 | 0.0297 | - |
| E09 | combined | pass | pass | pass | A+ | search_docs run_sql | 10.9 | 0.0367 | - |
| E10 | combined | pass | pass | pass | B+ | run_sql search_docs | 15.8 | 0.0695 | - |
| E11 | combined | pass | pass | pass | A | run_sql search_docs | 7.9 | 0.0244 | - |
| E12 | combined | pass | pass | pass | A | run_sql search_docs | 10.8 | 0.0407 | - |
| E13 | decline | pass | pass | pass | A+ | search_docs run_sql | 10.3 | 0.0424 | - |
| E14 | decline | pass | pass | pass | B+ | run_sql search_docs | 40.9 | 0.1734 | - |
| E15 | decline | pass | pass | pass | A | search_docs run_sql | 19.0 | 0.0645 | - |
| E16 | trap | fail | fail | fail | D | run_sql | 8.2 | 0.0343 | missing 'Stonefinch Fuel Stop'; missing 'TRV-KIWI-C12'; judge fail: The answer says No, but the reference says Yes: Stonefinch Fuel Stop has an authorized promotion from Nov 30 to Dec 13, 2026, listed under the variant spelling TRV-KIWI-C12, and the answer neither finds that promotion nor flags the SKU mismatch. |
| E17 | trap | fail | fail | fail | C | run_sql search_docs | 16.1 | 0.0476 | missing number 812; missing number 51008; judge fail: The May/June/July PO counts (205/0/194) and the conclusion that June was not zero demand are right, but the answer reports only 'cases sold' (about 50,047) instead of the required 812 rows and 51,008 cases across all depletion reasons, and it frames June as a real zero-intake month met by earlier orders rather than a missing month of order data. |
| E18 | trap | pass | pass | pass | B+ | run_sql search_docs | 13.9 | 0.0555 | - |
| E19 | trap | pass | pass | pass | A | run_sql | 2.9 | 0.0125 | - |
| E20 | trap | pass | pass | pass | A | search_docs run_sql | 17.9 | 0.0482 | - |
| E21 | sql | pass | pass | pass | A- | run_sql | 5.0 | 0.0195 | - |
| E22 | sql | pass | pass | pass | A | run_sql | 5.0 | 0.0178 | - |
| E23 | sql | pass | pass | pass | A | run_sql | 5.2 | 0.0213 | - |
| E24 | sql | pass | pass | pass | A+ | run_sql | 14.2 | 0.0420 | - |
| E25 | sql | pass | pass | pass | A+ | run_sql | 2.7 | 0.0148 | - |
| E26 | sql | pass | pass | pass | A | run_sql | 4.5 | 0.0210 | - |
| E27 | docs | pass | pass | pass | A+ | search_docs | 5.1 | 0.0191 | - |
| E28 | docs | pass | pass | pass | A- | search_docs | 4.3 | 0.0217 | - |
| E29 | docs | pass | pass | pass | A+ | search_docs | 3.8 | 0.0191 | - |
| E30 | docs | pass | pass | pass | A | search_docs | 3.5 | 0.0196 | - |
| E31 | combined | fail | fail | pass | A+ | search_docs run_sql | 8.8 | 0.0332 | missing number 98.6 |
| E32 | combined | pass | pass | pass | A | run_sql search_docs | 5.4 | 0.0221 | - |
| E33 | combined | fail | fail | pass | A | run_sql | 7.3 | 0.0257 | did not call search_docs; did not cite PRD-LMR-PUN-v1 |
| E34 | combined | pass | pass | pass | A- | run_sql search_docs | 9.0 | 0.0427 | - |
| E35 | decline | pass | pass | pass | A | run_sql search_docs | 6.5 | 0.0225 | - |
| E36 | decline | pass | pass | pass | A- | run_sql | 5.2 | 0.0308 | - |
| E37 | decline | pass | pass | pass | A | run_sql search_docs | 8.9 | 0.0231 | - |
| E38 | trap | pass | pass | pass | A+ | search_docs run_sql | 20.8 | 0.0579 | - |
| E39 | trap | pass | pass | pass | B+ | run_sql | 4.5 | 0.0144 | - |
| E40 | trap | pass | pass | pass | A+ | run_sql | 5.6 | 0.0232 | - |
| E41 | sql | pass | pass | pass | A- | run_sql | 8.6 | 0.0202 | - |
| E42 | sql | pass | pass | pass | A- | run_sql | 3.2 | 0.0145 | - |
| E43 | docs | fail | pass | fail | C | search_docs | 22.5 | 0.1136 | judge fail: Owner, helper, same-day response, the 24-hour escalation to the Product VP and the further 24-hour step to ownership all match the reference, but the answer adds that the Product VP and Commercial VP settle it together, which brings in the Commercial VP that the notes say is not the escalation destination. |
| E44 | docs | pass | pass | pass | A | search_docs | 6.1 | 0.0215 | - |
| E45 | combined | pass | pass | pass | A | run_sql search_docs | 7.0 | 0.0212 | - |
| E46 | combined | pass | pass | pass | A+ | search_docs run_sql | 19.3 | 0.0493 | - |
| E47 | decline | fail | fail | fail | F | search_docs run_sql | 21.8 | 0.1155 | missing 'profit'; did not cite POL-02-v1; stopped: step_cap; judge fail: The agent hit its step limit and gave no answer, so it neither stated the net-profitability criterion nor declined the ranking because the profitability data is missing. |
| E48 | decline | pass | pass | pass | A | run_sql search_docs | 14.8 | 0.0369 | - |
| E49 | trap | pass | pass | pass | A | run_sql search_docs | 13.9 | 0.0355 | - |
| E50 | trap | pass | pass | pass | A+ | run_sql search_docs | 7.0 | 0.0214 | - |
