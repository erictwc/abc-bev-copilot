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
