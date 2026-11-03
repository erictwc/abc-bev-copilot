# Decisions

Dated, one per entry. Newest at the bottom. Entries marked "tried, did not work" count toward the three required.
These first entries came from the design session on 2026-11-02; Eric made each decision.

## 2026-11-02 D1. Build the order-to-shelf copilot as the flagship
Extends the shipped PO status tool idea to a fuller supply-chain question set. Chosen over a generic beverage insights agent because it is a project Eric can speak to from real experience.

## 2026-11-02 D2. 100% synthetic data, fictional company ABC-BEV-CO
No real company data and no real company names in the repo. "Imagine Bev" was considered and dropped after a name check found a nearby real brand. (The real names are left out on purpose: the repo carries no real company names.)

## 2026-11-02 D3. Three model paths: local Qwen, cloud Qwen, Claude API
Local runs on the GEEKOM A5 (CPU only, 16 GB RAM) as an overnight batch. The comparison is the basis for a build-vs-buy memo.

## 2026-11-02 D4. Thin model adapter under 100 lines, no library wrapper
So Eric can explain how model calls, tools and retries work. Revisit only with a written reason.

## 2026-11-02 D5. Hard $20/month spend cap, enforced in code
$5 of it reserved for the v2 demo.

## 2026-11-02 D6. Eval authorship: Eric hand-writes 20, Claude Code drafts 20 for review
Judge model differs from the model under test. Eric spot-checks 10 judge calls.

## 2026-11-02 D7. Written pass bar before the first full run
Claude path at least 85% overall; 100% on must-decline and injection. No bar for Qwen paths; report as measured.

## 2026-11-02 D8. Staging: v1 before any interview; v2 after
v1: SQL tool, retrieval, 40 evals, cost log, three-way comparison, memo. v2: access control, injection defense, router, promo ROI, MCP, hosted demo, adoption.

## 2026-11-02 D9. Promo ROI (scenario B) enters in v2 as a second question family
Same tools and adapter, plus one table. It does not become a second app.

## 2026-11-02 D10. GPU performance is projected from the box, not claimed
Decode scales with memory bandwidth, prefill with compute. Published as ranges labeled "projected, not measured". Optional one-hour GPU rental to validate.

## 2026-11-02 D11. Hosted demo: Claude and cloud Qwen live, local Qwen as labeled replay
The GEEKOM box is never exposed to the open internet.

## 2026-11-02 D12. Adoption in v2: written guides, a recorded training, and a small pilot with 2 or 3 people
Log what the first users asked and where they got confused.

## 2026-11-02 D13. Eric writes the build-vs-buy memo
Claude Code can produce the numbers; the recommendation and judgment are Eric's.

## 2026-11-02 D14. Describe the beta-testing experience generically
"Beta user for third-party LLM testing: logging and categorizing failures." Check with his manager before it goes on a public page. Nothing from that tool appears in the repo.

## 2026-11-02 D15. Secret scan is a dependency-free pre-commit hook, not gitleaks
`.githooks/pre-commit` is plain Python (standard library only): it reads the staged diff and blocks key-shaped strings and any staged `.env` file. Chosen over gitleaks because it adds no dependency and every line can be read and explained. Accepted trade-off: far fewer patterns than gitleaks, and `git commit --no-verify` skips it. `make setup` turns it on (git does not copy hooks into a clone); `make test-secret-scan` proves it from a fresh clone.

## 2026-11-02 D16. The no-real-names rule covers the beverage business, not the tool stack
No real beverage brand, distributor, retailer, co-packer or employer appears in the repo. The two real names that D2 originally cited were removed from the repo copy; the decision itself is unchanged. Naming the tools and vendors the system is built on (Anthropic, Claude, Qwen, Ollama, DuckDB and the like) is fine: the spec cannot describe a three-way model comparison without them.

## 2026-11-02 D17. Generated tables are CSV files, committed to the repo
`make data` writes plain CSV with the standard library to `data/csv/`. A test before T1 built the same 50,000-row table twice: the `.duckdb` file hashed differently each run (DuckDB 1.5.6 and 2.0.0), CSV hashed the same on both runs and both versions, and Parquet was stable per run but changed bytes between versions. So a `.duckdb` file cannot meet "same seed, byte-identical output", and Parquet would tie the hashes to one library version. The CSVs are committed so eval cases can point at exact rows and any generator change shows as a data diff. DuckDB loads them in T5 with explicit column types; the `.duckdb` file stays a gitignored build product.

## 2026-11-02 D18. T1 uses the Python standard library only
No dependency is added for the generator. Adding DuckDB is its own decision in T5, when `run_sql` needs it. The planted-problem proofs in `docs/DATA.md` are written as DuckDB SQL so they can be reused by evals; for T1 they were run with a throwaway DuckDB outside the repo.

## 2026-11-02 D19. Data is anchored to 2026-10-31 with one fixed seed
Every date is computed from the constant `ANCHOR = 2026-10-31`, never from today's date: 24 full months of orders (Nov 2024 to Oct 2026), "next month" is November 2026, and an October promo has finished, which suits the v2 promo-ROI question. All randomness comes from one seeded `random.Random`; the committed data uses the default seed (`make data SEED=n` can override it for experiments). Shape defaults accepted with it: about 40 SKUs across 4 brands, 12 distributors, 3 warehouses with a snapshot every Monday, and `retailer` is the parent company while `chain` is the store banner. `make data-check` generates twice into temporary folders and compares hashes.

## 2026-11-02 D20. Where the five planted problems go
Each gets an ID (DP-01 to DP-05) in `docs/DATA.md` with its table, the exact rows and a proving query; nothing in the data itself marks them. DP-01: one SKU's ID is spelled differently in `promo_calendar` than in `sku_master`. DP-02: `distributor_orders` has no rows for one month. DP-03: a PO marked shipped for a launch SKU whose only co-packer run was cancelled, linked by SKU and week, with no schema change. DP-04: two distributors share a name prefix, kept as plain names as the spec lists them. DP-05: a November 2026 promo has an empty (NULL) `authorized` field rather than `n`.

## 2026-11-02 D21. DOC-IDs carry a type prefix and a version: `POL-01-v1`
`MET-01` is the metric library, `POL-01` to `POL-06` the six policies, `PRD-<brand>-<flavor>` a product sheet (codes from `sku_master`, e.g. `PRD-TRV-KIW`), and `OPS-01` an operations note. Every ID ends in a version, starting at `-v1`, so that a v2 revision (V4) can be cited separately from the text it replaced. Chosen over flat `DOC-001` numbers and over unversioned typed IDs. Default accepted with it: one file per document, and the filename carries no version, so a revision bumps the DOC-ID and the effective date in place and git history keeps the old text. T5 cites passages as `<DOC-ID>#<chunk>`.

## 2026-11-02 D22. Corpus files are Markdown with a plain `Key: value` header
The first four lines are `DOC-ID:`, `Title:`, `Owner:` and `Effective date:` (ISO date), then a blank line and the body. The filename is the lowercased DOC-ID without its version plus a slug, e.g. `pol-01-po-change.md`. Chosen over YAML front matter, which would need PyYAML to parse properly, and over plain text, which has no headings to chunk on. The corpus is every `docs_corpus/*.md` except `README.md`.

## 2026-11-02 D23. Product sheets come from a committed standard-library script, run by `make corpus`
`docs_corpus/make_sheets.py` reads `data/csv/sku_master.csv` and writes one sheet per flavor (20 sheets, both packs on each), byte-identical on every run. It has its own `make corpus` and `make corpus-check` targets and is not folded into `make data`, so the accepted T1 recipe is unchanged. Chosen over a one-off script whose output alone is committed.

## 2026-11-02 D24. Product sheets add invented specs beyond `sku_master`
Each sheet lists the `sku_master` facts (brand, flavor, sku_id per pack, case size, co-packer line, status) plus caffeine, calories, sugar and shelf life. These figures are invented, exist only in the sheets, and come from one seeded `random.Random` in the script, so they are stable. Chosen over `sku_master` facts only, to give retrieval questions that SQL cannot answer. No UPCs, because an invented UPC could belong to a real product. Sheets cite only `sku_master` IDs and say nothing about runs, POs or promos, so no sheet hints at DP-01 to DP-05.

## 2026-11-02 D25. The injection trap is an ordinary-looking operations note
`OPS-01-v1`, a Q4 receiving and holiday note, carries the injection sentence in the middle of its body, not in the header. The payload tells the agent to state that all open POs are confirmed and to quote a reference code; the code appears nowhere else, so an eval can detect a hijack by exact string match rather than by a judge. Its topic avoids every planted data problem. That this file is the trap, and its code, are recorded only in `docs/CORPUS.md`, outside the corpus, as `docs/DATA.md` does for the data. Chosen over hiding the sentence in a product sheet and over a payload that only tries to leak the system prompt, which needs a judge to score.

## 2026-11-02 D26. Eric's seven documents start as header-only stubs
Claude Code creates the metric library and the six policy files with their headers and a one-line placeholder; Eric writes every body, owner and effective date. `docs/CORPUS.md` lists, outside the corpus, what each document has to cover for the planned questions. T2 is not done until Eric has filled them in and confirmed they are his own.

## 2026-11-02 D27. Eric's seven documents are drafted from his interview answers
Eric sets every rule, threshold, owner and definition in the metric library and the six policies by answering questions, one document at a time. Claude Code drafts the document from his answers only, marks anything he did not answer as `[GAP: ...]` instead of filling it in, and Eric reviews and corrects every line before it counts. His answers are kept in `docs/interviews/`, outside the corpus, so every rule traces back to what he said. Chosen over Eric typing all seven himself (D26's plan) and over a mix. It changes the claim in SPEC §11, the README and the narrative to: "I set every policy rule and metric definition in a structured interview; Claude Code drafted the documents from my answers, and I reviewed and edited every line." The eval cases stay hand-written (D6). D26's stubs and the T2 done-when, Eric confirming the policies are his own, are unchanged.
