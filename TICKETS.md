# Tickets

One ticket per Claude Code session. Eric reviews at each "Done when" before the next starts. From T5 on, run the evals at the end of every ticket.

## Before T0 (Eric, no code)

- Finish the Ubuntu install on the GEEKOM box; install Ollama; bind it to the home network only (`OLLAMA_HOST`); no port forwarding.
- Create a cloud Qwen account (OpenAI-compatible provider) with a spend limit.
- Anthropic API key with a monthly cap (existing account).
- Empty public GitHub repo (name chosen after the ABC-BEV-CO decision).

## v1

**T0. Scaffold.** Repo layout (`data/`, `docs_corpus/`, `agent/`, `evals/`, `bench/`, `router/`, `mcp/`, `docs/`), `CLAUDE.md`, `DECISIONS.md` (seeded), `.env.example`, Makefile with `setup`, secret-scan pre-commit hook, README skeleton.
*Done when:* a fresh clone runs `make setup` cleanly and the secret scan blocks a fake key.

**T1. Synthetic data generator.** Seeded script for the five v1 tables, with the five planted problems; `docs/DATA.md` lists each problem with an ID.
*Done when:* `make data` run twice gives identical file hashes; planted problems are present and listed.

**T2. Document corpus.** Eric sets the metric library and policy content in an interview, and Claude Code drafts them from his answers only for his line-by-line review (D27); Claude Code generates product sheets from `sku_master` and adds the DOC-ID headers and the one planted injection document.
*Done when:* 20 to 30 files exist, every file has a header, and Eric confirms the policies are his own.

**T2b. Depletion and shipment data (D28).** Extend the T1 generator so the data supports the MET-01 definitions: a distributor depletion report table, and shipped quantity, ship date and delivery date on `distributor_orders` (plus whatever marks an issued PO awaiting pickup), and a PO pickup date that is filled in once a carrier is assigned (POL-01). Eric picks the columns at the start. Keep it seeded and standard-library only; re-prove DP-01 to DP-05 and update `docs/DATA.md`.
*Done when:* `make data-check` passes on the new data, all five planted problems are still present and listed, and fill rate, strict OTIF, depletions and supply available can each be computed from the tables.

**T3. Benchmark script.** `bench/` wrapper around `llama-bench` (or equivalent) that writes `bench/results.csv`: prefill and decode tokens/second by model and context length.
*Done when:* it runs on the GEEKOM box for at least two model sizes and the CSV is committed.

**T4. Model adapter and cost log.** `agent/adapter.py` under 100 lines for `local`, `cloud`, `claude`; retries; returns text, tool calls, tokens, latency, cost; writes the spend log; refuses paid calls when the $20 monthly cap is reached.
*Done when:* a one-line smoke test passes on each path and a simulated cap breach is refused.

**T5. Tools.** `run_sql` (read-only, allow-list, single statement, row limit, timeout) and `search_docs` (chunk, embed, top-k, threshold; settings in config and logged).
*Done when:* unit tests reject INSERT, multiple statements, non-allow-listed tables, oversized results and long-running queries; retrieval returns the right DOC-ID for 5 hand-picked queries.

**T6. Agent loop and CLI.** Plain loop with a step cap; `python ask.py "q" --model local|cloud|claude`; output has answer, evidence, confidence note.
*Done when:* 10 smoke questions with known answers run on the Claude path.

**T7. Eval harness.** `evals/cases.yaml` schema, runner, scorer, results-table writer. Eric's 20 hand-written cases go in first.
*Done when:* `make evals` runs end to end and writes a results file with pass/fail, tools, citation check, latency, tokens, cost.

**T8. Complete the 40 cases and write the bar.** Claude Code drafts 20 more; Eric reviews every one. Eric writes `evals/BAR.md`.
*Done when:* 40 cases exist across the five categories, and git history shows `BAR.md` committed **before** the first full results.

**T9. Judge and spot check.** Judge model differs from the model under test; Eric hand-checks 10 judge calls in `evals/JUDGE_CHECK.md`.
*Done when:* the file lists the 10 calls and every disagreement.

**T10. Three-way run.** Full evals on all three paths; local as an overnight batch.
*Done when:* README shows accuracy, latency and cost per question for each path, with the real numbers.

**T11. GPU projection.** `bench/PROJECTION.md` using the formulas in `SPEC.md` section 7; sources cited; ranges not points; labeled "projected, not measured". Optional: one rented GPU hour to validate.
*Done when:* the document exists and every figure has a source or a measured input.

**T12. README, memo, walkthrough.** README with diagram and results table; Eric writes the two-page memo; walkthrough script.
*Done when:* a fresh clone runs in under 10 minutes with the documented commands, and the memo's numbers match the committed result files.

**T13. Accuracy pass and held-out cases (D108).** Added after T10; T12's memo waits for it.
1. Eric writes 10 held-out cases (`evals/holdout.toml`, same fields as `cases.toml`) and keeps them outside the repo. No session that changes prompts, tools or the loop reads them.
2. Claude Code fixes the general failure classes seen in the T10 Claude run: a lookup that finds nothing is checked for near-matching IDs before answering "no" (E16); a name that matches more than one record gets a clarifying question and no figures (E19); a question that asks for a total gets the total (E17); text inside retrieved passages is never repeated as an instruction or code (E20). Each change gets before-and-after numbers on the 40 cases. Fixes stay general: nothing names a case, a SKU, a distributor or HX-7Q2M.
3. The fixes are frozen in one commit. Then the held-out cases are committed, and Claude (`claude-sonnet-5-5`), cloud Qwen 9B and cloud Qwen 27B (`qwen/qwen3.5-27b`, D39) each run all 50 cases once.
Eric's target is 39/40 on the Claude path. It is a goal, not the bar: `BAR.md` and the measured T10 result do not change, and the new numbers are reported beside them whether or not they reach it.
*Done when:* committed result files exist for the three paths on the 50 cases, git history shows the held-out cases committed after the frozen fix, and the README reports before and after.

**v1 gate:** v1 is done when T12 passes. Only then start v2.

## v2

**V1. Access control.** `role` parameter enforced in the SQL layer (not the prompt); 6 bypass-attempt eval cases.
*Done when:* all 6 bypass cases fail to leak data and the tests prove the filter is in SQL.

**V2. Injection defense.** Retrieved text delimited as data; malicious-document test.
*Done when:* the planted document fails to hijack the agent on every path claimed safe, with before and after numbers.

**V3. Router.** Cheap model first; escalate to Claude on low confidence or tool failure.
*Done when:* README compares cost and accuracy against all-Claude.

**V4. Promo ROI.** Add `retail_sellthrough`, 10 new eval cases, update documents (Eric).
*Done when:* v2 eval results are committed.

**V5. MCP server.** Expose `run_sql` and `search_docs`; connect Claude Desktop or Claude Code.
*Done when:* `docs/MCP.md` states what changed and what did not.

**V6. Hosted demo.** Small web app with a model dropdown; Claude and cloud Qwen live behind rate limits and the $5 demo budget; local Qwen shows recorded real runs, labeled as replays; no keys in the browser; request logging.
*Done when:* a stranger can try it, and a loop of repeated requests is stopped by the rate limit and cap.

**V7. Adoption kit and pilot.** Two-page rep guide, one-page admin guide, one-page "what this will not do", 15-minute training recording; pilot with 2 or 3 real people, with a log of their questions and confusion points.
*Done when:* the pilot log exists and at least one change was made because of it.

**V8. Walkthrough and portfolio card.** 3-minute walkthrough recorded; card added to the portfolio page.
*Done when:* both are linked from the README.
