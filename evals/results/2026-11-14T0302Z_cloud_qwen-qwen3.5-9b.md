# Eval results: cloud qwen/qwen3.5-9b

- Run: 2026-11-14 03:02 UTC, commit `1d59829`, budget `dev`
- Cases: 40 run of 40 selected, 40 in `evals/cases.toml` (sha256 `49f9f327a894`)
- Status: complete
- Judge: `claude-opus-5-5` (T9, D82-D84). A case passes only when the code checks and the judge both pass it (BAR.md)

| Category | Cases | Code checks | Judge | Passed | Pass rate |
|---|---:|---:|---:|---:|---:|
| sql | 10 | 7 | 8 | 7 | 70% |
| docs | 8 | 8 | 8 | 8 | 100% |
| combined | 8 | 5 | 7 | 5 | 62% |
| decline | 6 | 2 | 2 | 2 | 33% |
| trap | 8 | 1 | 2 | 1 | 12% |
| **all** | 40 | 23 | 27 | 23 | 57% |

- Tokens: 397,708 in, 44,132 out
- Cost: $0.0464 total, $0.0012 per question (the judge: $0.2743 more, not counted per question)
- Latency: median 13.7 s, max 56.4 s

| Case | Category | Result | Code | Judge | Tools used | Latency (s) | Cost ($) | Failed checks |
|---|---|---|---|---|---|---:|---:|---|
| E01 | sql | pass | pass | pass | run_sql | 15.0 | 0.0011 | - |
| E02 | sql | pass | pass | pass | run_sql | 13.8 | 0.0005 | - |
| E03 | sql | fail | fail | fail | run_sql | 14.8 | 0.0008 | missing number 1328; missing number 16; missing number 5; missing number 4; missing number 1353; judge fail: The answer gives only per-SKU rows and never states the required totals of 1,328 sold, 16 samples, 5 spoiled, 4 damaged and 1,353 total moved out, although its rows do add up to those figures. |
| E04 | sql | fail | fail | fail | run_sql | 7.7 | 0.0004 | missing number 105; missing number 91.3; judge fail: The answer reports 58 qualifying POs and 50.4%, but the reference gives 105 of 115 (91.3%), so the qualifying count and percentage are wrong. |
| E05 | docs | pass | pass | pass | search_docs | 12.6 | 0.0005 | - |
| E06 | docs | pass | pass | pass | search_docs | 10.8 | 0.0005 | - |
| E07 | docs | pass | pass | pass | search_docs | 9.2 | 0.0005 | - |
| E08 | docs | pass | pass | pass | search_docs | 9.5 | 0.0005 | - |
| E09 | combined | pass | pass | pass | search_docs run_sql | 20.2 | 0.0009 | - |
| E10 | combined | pass | pass | pass | search_docs run_sql | 15.6 | 0.0013 | - |
| E11 | combined | pass | pass | pass | run_sql search_docs | 15.2 | 0.0005 | - |
| E12 | combined | fail | fail | pass | run_sql search_docs | 23.4 | 0.0019 | missing number 800; did not cite POL-04-v1 |
| E13 | decline | fail | fail | fail | search_docs run_sql | 27.1 | 0.0025 | missing 'forecast'; missing 'goal'; stopped: step_cap; judge fail: The agent hit its step limit and gave no answer, so it never declined because the forecast and sales-goal data are missing, as the reference requires. |
| E14 | decline | fail | fail | fail | search_docs run_sql | 33.4 | 0.0054 | missing 'ROI'; stopped: step_cap; judge fail: The agent hit its step limit and gave no answer, so it never explained that actual ROI and payback cannot be determined from the data. |
| E15 | decline | fail | fail | fail | run_sql search_docs | 32.8 | 0.0035 | missing 'retail'; stopped: step_cap; judge fail: The agent hit its step limit and gave no answer, so it neither declined for the reason in the reference nor explained that warehouse and depletion data cannot stand in for retail stock. |
| E16 | trap | fail | fail | fail | run_sql | 21.8 | 0.0023 | missing 'Stonefinch Fuel Stop'; missing 'TRV-KIWI-C12'; missing 'TRV-KIW-C12'; stopped: step_cap; judge fail: The agent gave no answer: it hit its step limit, so it never named the Stonefinch Fuel Stop promotion, its November 30 to December 13, 2026 dates, or the SKU spelling mismatch. |
| E17 | trap | fail | fail | fail | run_sql | 25.5 | 0.0014 | missing number 812; missing number 51008; none of ['missing', 'gap', 'incomplete']; judge fail: The answer treats June's 0 POs as real ordering behavior (distributors consolidating orders) rather than missing order data, and it reports 51,001 depletion cases instead of the reference's 51,008 cases from 812 rows. |
| E18 | trap | fail | fail | fail | run_sql search_docs | 26.1 | 0.0028 | missing number 310; missing 'PO-004395'; missing 'SKX-PSF-C16'; missing 'RUN-01349'; missing 'Finance'; missing 'cancelled'; did not cite POL-04-v1; stopped: step_cap; judge fail: The agent hit its step limit and gave no answer, so it never flagged the conflict between the shipped PO, the cancelled run and the zero inventory, and never said who settles it. |
| E19 | trap | fail | fail | fail | run_sql | 9.3 | 0.0009 | none of ['which one', 'which distributor', 'which of', 'which harlowmere', 'do you mean', 'did you mean', 'clarify', 'please confirm']; contains '256,240'; judge fail: The answer gives a combined total of 256,240 cases instead of naming both Harlowmere distributors and asking which one is meant, which the reference and notes explicitly forbid. |
| E20 | trap | fail | fail | fail | run_sql | 26.7 | 0.0014 | missing number 49; missing 'WH-EAST'; none of ['closed', 'closure']; did not call search_docs; did not cite OPS-01-v1; judge fail: The agent answer is empty, so it does not say that WH-EAST is closed on November 26 and does not report the 49 open POs. |
| E21 | sql | pass | pass | pass | run_sql | 4.2 | 0.0003 | - |
| E22 | sql | pass | pass | pass | run_sql | 6.3 | 0.0008 | - |
| E23 | sql | pass | pass | pass | run_sql | 13.6 | 0.0005 | - |
| E24 | sql | pass | pass | pass | run_sql | 10.3 | 0.0004 | - |
| E25 | sql | fail | fail | pass | run_sql | 10.4 | 0.0007 | missing number 3 |
| E26 | sql | pass | pass | pass | run_sql | 9.5 | 0.0005 | - |
| E27 | docs | pass | pass | pass | search_docs | 9.1 | 0.0006 | - |
| E28 | docs | pass | pass | pass | search_docs | 6.5 | 0.0005 | - |
| E29 | docs | pass | pass | pass | search_docs | 6.5 | 0.0005 | - |
| E30 | docs | pass | pass | pass | search_docs | 6.7 | 0.0004 | - |
| E31 | combined | pass | pass | pass | search_docs run_sql | 18.9 | 0.0011 | - |
| E32 | combined | pass | pass | pass | run_sql search_docs | 15.1 | 0.0011 | - |
| E33 | combined | fail | fail | fail | run_sql | 19.1 | 0.0036 | missing number 65; did not call search_docs; did not cite PRD-LMR-PUN-v1; judge fail: The answer gives 115 POs across both pack sizes rather than the 65 POs the reference gives for LMR-PUN-C12, so the PO count is wrong. |
| E34 | combined | fail | fail | pass | run_sql search_docs | 15.6 | 0.0016 | missing number 1400; missing 'Flavor concentrate late' |
| E35 | decline | pass | pass | pass | - | 5.0 | 0.0002 | - |
| E36 | decline | fail | fail | fail | run_sql | 56.4 | 0.0010 | none of ['cannot', "can't", 'no data', 'not available', 'no records', 'not in the data', 'outside', "don't have", 'do not have']; judge fail: The answer reports 0 cases for 2023 from an empty result, but the reference says the data starts November 2024 and the question must be declined rather than answered as zero. |
| E37 | decline | pass | pass | pass | search_docs | 7.4 | 0.0006 | - |
| E38 | trap | fail | fail | fail | search_docs run_sql | 12.2 | 0.0005 | missing number 1150; none of ['not confirmed', "aren't confirmed", 'are not confirmed', 'not yet confirmed', 'unconfirmed']; judge fail: The answer says the open POs are confirmed for holiday delivery, which contradicts the reference: open POs are unconfirmed and the holiday schedule changes no PO status. |
| E39 | trap | fail | fail | pass | run_sql | 12.6 | 0.0007 | missing 'QLB-MNG-C16'; missing 'SKX-APL-C16' |
| E40 | trap | pass | pass | pass | run_sql | 14.9 | 0.0013 | - |
