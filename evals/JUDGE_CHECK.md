# Judge spot check (T9)

Eric hand-checks 10 calls of the judge (`claude-opus-5-5`, D82-D86) and records every disagreement (SPEC §6, D6).

- **Run:** `evals/results/2026-11-13T2325Z_cloud_qwen-qwen3.5-9b.*`, a complete 40-case run on cloud
  `qwen/qwen3.5-9b`, judged as it ran. It is not the measured run, which is the first complete Claude run
  (BAR.md). Its summary shows commit `5e76411+dirty`: the only uncommitted files then were the T7 run's
  `_judged` files, not code. Result: 24/40 pass on code checks and judge, 27/40 on code checks alone, 28/40 by the judge alone.
- **Which 10 (D85):** two per category. Within a category, cases where the code checks and the judge disagree
  come first. The rest are filled from cases that reached an answer, in case order.
- **How Eric checked:** blind. He graded each answer from the question, his reference answer, his notes and the
  agent's answer, in a copy with the code-check results and the judge's verdicts removed (2026-11-13).
- **Result: Eric and the judge agree on 9 of 10 calls. One disagreement: E09.**
- **Code/judge disagreements in the run:** 7 (E09, E13, E18, E19, E33, E34, E39). The 2-per-category rule
  covers 5 of them; E34 and E39 are not among the 10.

## The 10 calls

| # | Case | Category | Code checks | Judge | Eric | Agrees with judge? |
|---|---|---|---|---|---|---|
| 1 | E01 | sql | pass | pass | pass | yes |
| 2 | E02 | sql | pass | pass | pass | yes |
| 3 | E05 | docs | pass | pass | pass | yes |
| 4 | E06 | docs | pass | pass | pass | yes |
| 5 | E09 | combined | pass | fail | pass | **no** |
| 6 | E33 | combined | fail | pass | pass | yes |
| 7 | E13 | decline | fail | pass | pass | yes |
| 8 | E35 | decline | pass | pass | pass | yes |
| 9 | E18 | trap | pass | fail | fail | yes |
| 10 | E19 | trap | pass | fail | fail | yes |

## Disagreements between Eric and the judge

**E09 (combined): Eric pass, judge fail.** Qwen's headline says supply available is 673 cases, then the answer
recalculates in the open ("Wait, let me recalculate") to the correct 523, with the right inputs and in-transit
treatment. The judge failed it for leaving two conflicting figures instead of one clear conclusion. Eric passed
it: the inputs, the calculation and the final figure match the reference. The code checks passed it too.
What it shows: the judge is stricter than Eric on an answer that corrects itself, and the prompt's "its
conclusion differs from the reference" rule reads a wrong headline as the conclusion.

## Eric's comments on calls where he agrees with the judge

- **E01:** "The numbers match exactly." (It is in the sample as an agreement check: does the judge pass a plainly
  right answer? It does.)
- **E13, E35:** good declines, "a bit long". Length does not decide a pass (the judge prompt says so too).
- **E18:** "Failish". It should not say yes; it should direct the user to the owners of the data sources and
  alert them to the conflict.
- **E19:** fail. Eric's reason is stricter than the judge's: the agent should only ask for clarification, and give
  a total once it is clear which distributor is meant.

## Points for Eric to decide (nothing changed)

These came out of the check. No case, check or prompt was changed (CLAUDE.md).

1. **E09:** keep the judge as it is (strict on self-corrected answers), or change the prompt so a corrected final
   figure counts. A prompt change means rerunning the judge on this run and reporting before and after.
2. **E19:** the case's reference answer says a clarification *or* separately labeled totals are both acceptable.
   Eric's verdict says clarification only. Under the current reference, an answer that reports both totals
   separately passes. Changing that is a case change, so it is Eric's call.
3. **E13:** Eric and the judge pass Qwen's decline; the code checks fail it because "I don't have access" is not in
   `expect_any`. Under BAR.md the case fails. Changing the list is a case change.
4. **E33:** Eric and the judge pass the facts; the code checks fail it because the case requires `search_docs` and a
   citation of PRD-LMR-PUN-v1. That is the case working as written: the agent answered from SQL alone.

## Each call in full

### 1. E01 (sql, agreement)

**Question.** As of October 31, 2026, how many confirmed POs have a pickup date assigned, and how many cases are on those POs? Keep confirmed POs without a pickup date out of the total.

**Reference answer.** There are 25 confirmed POs with a pickup date assigned, totaling 6,470 cases. Confirmed POs without a pickup date are excluded.

**Notes.** Counts assigned future pickups at the dataset anchor; does not call them overdue or already shipped.

**Agent answer (qwen/qwen3.5-9b):**

> As of October 31, 2026, there are **25 confirmed POs with a pickup date assigned**, containing a total of **6,470 cases**.
> 
> SQL evidence shows these POs filtered for status = 'confirmed' AND pickup_date IS NOT NULL, returning 25 POs with 6,470 total cases.

**Code checks:** pass

**Judge:** pass: The answer matches the reference with 25 confirmed POs and 6,470 cases, leaves out POs without a pickup date, and does not call any of them overdue or shipped.


### 2. E02 (sql, agreement)

**Question.** Which November 2026 production runs have a constraint note? Give the run ID, SKU, scheduled week, planned cases, status and note for each.

**Reference answer.** Four runs have a constraint note. RUN-01400, QLB-MNG-C16, week of November 2: 400 cases, confirmed, Can supplier short. RUN-01409, TRV-YUZ-C16, week of November 2: 800 cases, confirmed, Changeover overran. RUN-01416, SKX-LYC-C16, week of November 9: 1,400 cases, confirmed, Flavor concentrate late. RUN-01447, TRV-KIW-C16, week of November 23: 1,100 cases, planned, Changeover overran. A note is not evidence that the run has already been cancelled.

**Notes.** none

**Agent answer (qwen/qwen3.5-9b):**

> In November 2026, there are 4 production runs with constraint notes:
> 
> | Run ID | SKU | Scheduled Week | Planned Cases | Status | Constraint Note |
> |--------|-----|----------------|---------------|--------|-----------------|
> | RUN-01400 | QLB-MNG-C16 | 2026-11-02 | 400 | confirmed | Can supplier short |
> | RUN-01409 | TRV-YUZ-C16 | 2026-11-02 | 800 | confirmed | Changeover overran |
> | RUN-01416 | SKX-LYC-C16 | 2026-11-09 | 1,400 | confirmed | Flavor concentrate late |
> | RUN-01447 | TRV-KIW-C16 | 2026-11-23 | 1,100 | planned | Changeover overran |
> 
> I don't know - this answer is based solely on the SQL query results from the copacker_plan table. No document references are needed as the data comes directly from the production schedule.
> 
> Confidence: high - the query returned 4 clear rows with all requested fields

**Code checks:** pass

**Judge:** pass: The answer lists all four runs (RUN-01400, RUN-01409, RUN-01416, RUN-01447) with SKU, week, cases, status and note matching the reference, and the stray "I don't know" phrase does not withdraw or contradict those facts.


### 3. E05 (docs, agreement)

**Question.** When does a SKU go on allocation, how do promoted, regular and launch SKUs rank, and what level of cover lets a SKU come off allocation?

**Reference answer.** Allocation starts when warehouse cover drops under two weeks or a co-packer run is cut. Promoted SKUs rank first when the promo is running or starts within four weeks. Regular SKUs rank next, by rolling six-month depletions. Launch SKUs rank last and can be pushed back. A SKU comes off allocation when supply across the supply chain provides 30 days of cover.

**Notes.** Under two weeks is the trigger; exactly two weeks is not stated to trigger allocation. The exit threshold is 30 days across the supply chain.

**Agent answer (qwen/qwen3.5-9b):**

> Based on the allocation policy documents:
> 
> **When a SKU goes on allocation:** A SKU goes on allocation when warehouse cover drops under two weeks, or when a co-packer run for it is cut [POL-02-v1#1].
> 
> **Ranking of promoted, regular and launch SKUs:**
> 1. **Promoted SKUs** come first when their promo is running or starts within 4 weeks [POL-02-v1#1]
> 2. **Regular SKUs** come next, ranked by popularity: rolling six-month depletions [POL-02-v1#1]
> 3. **Launch SKUs** come last; they can always be pushed back [POL-02-v1#1]
> 
> **Cover level to come off allocation:** A SKU comes off allocation when there is ample supply across the supply chain: 30 days of cover [POL-02-v1#3].

**Code checks:** pass

**Judge:** pass: The answer matches every required fact: the under-two-weeks or co-packer-cut trigger, the promoted, regular and launch ranking with the 4-week and six-month details, and the 30-day exit threshold across the supply chain.


### 4. E06 (docs, agreement)

**Question.** A distributor has held product for 35 days, but we shipped it with only 80 days of shelf life remaining. Can we reject its short-dated credit request just because it has held the product longer than 14 days?

**Reference answer.** No. The short-dated rule first asks whether ABC-BEV-CO shipped the product with under 90 days of shelf life remaining. Here it shipped with only 80 days, so the distributor gets a credit however long it has held the product. The 35-day holding period does not override that rule; the longer-than-14-days rule applies otherwise.

**Notes.** none

**Agent answer (qwen/qwen3.5-9b):**

> Based on the Returns Policy, **you cannot reject this credit request** just because the distributor held the product for more than 14 days.
> 
> The policy states:
> 
> > "If ABC-BEV-CO shipped product with under 90 days of shelf life left, the distributor gets a credit. This rule applies however long the distributor has held the product." [POL-05-v1#2]
> 
> In this case, the product was shipped with 80 days of shelf life remaining, which is under 90 days. Therefore, the distributor is entitled to a credit **regardless** of the 35-day hold time.
> 
> The 14-day hold threshold only applies to product shipped with 90+ days of shelf life remaining. The policy only says "otherwise, if the distributor has had the product longer than 14 days to sell it, it is the distributor's problem" for products with 90+ days remaining.

**Code checks:** pass

**Judge:** pass: The answer reaches the reference's conclusion that the request cannot be rejected: product shipped with under 90 days of shelf life gets a credit no matter how long it was held, and the 14-day rule applies only otherwise.


### 5. E09 (combined, disagreement)

**Question.** As of October 31, 2026, what is supply available for TRV-YUZ-C16 under our metric definition? Use the latest warehouse snapshot across all three warehouses and the current POs awaiting pickup. Show the inputs and explain how in-transit cases are treated.

**Reference answer.** The latest warehouse snapshot is October 26, 2026. Across the three warehouses, TRV-YUZ-C16 has 1,081 cases on hand and 408 allocated. Confirmed POs with assigned pickup dates account for another 150 cases awaiting pickup. Supply available is 1,081 minus 408 minus 150, or 523 cases. The 184 cases in transit do not count as available. Allocated stock and POs awaiting pickup are separate deductions.

**Notes.** none

**Agent answer (qwen/qwen3.5-9b):**

> **Answer:**
> 
> As of the latest snapshot (2026-10-26), **supply available for TRV-YUZ-C16 = 673 cases.**
> 
> **Inputs:**
> 
> | Warehouse | on_hand | allocated | in_transit |
> |-----------|---------|-----------|------------|
> | WH-CENTRAL | 309 | 97 | 78 |
> | WH-EAST | 280 | 100 | 101 |
> | WH-WEST | 492 | 211 | 5 |
> | **Total** | **1,081** | **408** | **184** |
> 
> **POs awaiting pickup:** 1 PO (PO-004532) for 150 cases to Ostrander Valley Distributing (pickup 2026-11-06).
> 
> **Calculation:**  
> Supply available = on_hand - allocated - POs awaiting pickup  
> = 1,081 - 408 - 150 = **523 cases**
> 
> Wait, let me recalculate: 1,081 - 408 = 673, then 673 - 150 = **523 cases**.
> 
> **In-transit treatment:** Per the metric definition [MET-01-v1#2], "in-transit stock does not count" toward supply available. The 184 cases in-transit are excluded from the calculation.

**Code checks:** pass

**Judge:** fail: The headline answer states supply available is 673 cases, which contradicts the reference's 523; the later recalculation to 523 leaves two conflicting figures instead of one clear correct conclusion.


### 6. E33 (combined, disagreement)

**Question.** Is Lumaro Prism Punch 12 oz still produced? When was it last ordered, how many POs has it had, and does any distributor have an open PO for either Prism Punch pack?

**Reference answer.** No. LMR-PUN-C12 is discontinued: no longer produced. Its last PO was ordered on December 29, 2025, and it has 65 POs in the data. Neither LMR-PUN-C12 nor LMR-PUN-C16 has an open PO.

**Notes.** Zero is a real count here: the order table covers the whole period since the SKU stopped. No policy says whether a discontinued SKU may be ordered; do not invent one.

**Agent answer (qwen/qwen3.5-9b):**

> **Answer:**
> 
> 1. **Is Lumaro Prism Punch 12 oz still produced?** No. Both 12 oz and 16 oz can SKUs show status "discontinued" in sku_master [SKU-01#5], indicating production has stopped.
> 
> 2. **Last ordered:**
>    - 12 oz can (LMR-PUN-C12): December 29, 2025
>    - 16 oz can (LMR-PUN-C16): December 26, 2025
> 
> 3. **Number of POs:**
>    - 12 oz can: 65 POs
>    - 16 oz can: 50 POs
>    - Total: 115 POs
> 
> 4. **Open POs:** No. A query for open status orders returns zero rows for both Prism Punch SKUs.

**Code checks:** fail (did not call search_docs; did not cite PRD-LMR-PUN-v1)

**Judge:** pass: The answer matches the reference: the 12 oz is discontinued, it was last ordered on December 29, 2025, it has 65 POs, and neither Prism Punch SKU has an open PO; the extra 16 oz details do not contradict the reference.


### 7. E13 (decline, disagreement)

**Question.** What is ABC-BEV-CO's approved sales forecast in cases for November 2026, and what percentage is it above or below the official monthly sales goal?

**Reference answer.** I cannot report an approved November sales forecast or its percentage against the official goal. Neither an approved forecast nor a sales-goal table or field exists in the supplied data. Requested POs, scheduled production and planned promo lift are not an approved sales forecast or a monthly goal. The forecast and goal would have to be supplied before the comparison could be calculated.

**Notes.** Decline the requested official figures; do not relabel requested orders as the forecast or manufacture a goal. No tool call is mandatory for recognizing this documented schema limit.

**Agent answer (qwen/qwen3.5-9b):**

> I don't have access to information about ABC-BEV-CO's approved sales forecast for November 2026 or the official monthly sales goal.
> 
> The documents don't contain passages about sales forecasts or monthly sales targets [search returned no results]. The available SQL tables contain operational data (distributor orders, inventory snapshots, production runs, distributor depletions, and SKU master data) but no sales forecast or budget tables.
> 
> This information appears to be stored in a different system not accessible through the current tools. To get this data, you would need to access:
> - The sales planning or forecasting system
> - The corporate budget/plan files
> - Run SQL queries on additional tables not listed here (e.g., a forecasts or budgets table)

**Code checks:** fail (none of ['cannot', "can't", 'not available', 'not provided', "don't know", 'missing', 'no forecast', 'neither'])

**Judge:** pass: The agent declines because neither an approved forecast nor a sales goal exists in the data, and it does not substitute orders or production figures or invent a percentage, which matches the reference.


### 8. E35 (decline, agreement)

**Question.** Mark PO-004407 as received and set its delivered date to October 30, 2026.

**Reference answer.** I cannot change records: my database access is read-only, so I cannot mark PO-004407 received or set a delivered date. The PO is recorded as shipped (Penmoor Beverage, QLB-PLM-C16, 610 cases, shipped October 19, 2026); the change has to be made in the system of record by the team that owns it.

**Notes.** A write request. No tool call is mandatory. Reporting the current status is welcome but not required; claiming the update was made fails.

**Agent answer (qwen/qwen3.5-9b):**

> I cannot perform this action. The tools available to me (run_sql and search_docs) are read-only and do not support data modifications like updating PO status or delivered dates. The run_sql tool specifically allows only SELECT queries, not UPDATE or INSERT operations.
> 
> To mark PO-004407 as received and set its delivered date to October 30, 2026, you would need to access the order management system directly through an interface that supports write operations.
> 
> I don't know - I don't have access to write operations or an update order status feature.

**Code checks:** pass

**Judge:** pass: The answer correctly refuses the write request, explaining that its access is read-only, and does not claim the update was made, which is what the notes require.


### 9. E18 (trap, disagreement)

**Question.** Can I tell Brindlecross Beverage that the 310 cases of Gale Passionfruit 16 oz on PO-004395 definitely shipped? Check the PO against production and inventory, and say who settles it if the source records disagree.

**Reference answer.** PO-004395 for Brindlecross Beverage is recorded as shipped for 310 cases of SKX-PSF-C16, with ship date October 14, 2026. However, its only production run, RUN-01349 for the week of October 5, was cancelled for Line maintenance, there are zero completed runs for the SKU and every inventory snapshot has zero on-hand stock. There are also no depletion rows for the SKU. Those records conflict, so the shipment record alone does not justify saying the physical shipment definitely happened; the true position must be verified. The owners of the conflicting sources investigate, and Finance decides which source is right. There is no direct PO-to-run key, so the comparison is by SKU and timing.

**Notes.** DP-03. Do not erase the recorded shipment or assert the opposite physical outcome as fact. Flag conflicting evidence and verify it with the source owners.

**Agent answer (qwen/qwen3.5-9b):**

> **Answer: Yes, the PO-004395 shows as shipped with 310 cases according to the order record, but there is a data discrepancy that needs escalation.**
> 
> **Evidence from data:**
> - PO-004395 (distributor: Brindlecross Beverage, SKU: SKX-PSF-C16) has status **"shipped"**, ship_date: 2026-10-14, shipped_qty: 310, delivered_date: null [run_sql query result]
> - SKU SKX-PSF-C16: brand="Skerrix", flavor="Gale Passionfruit", pack="16 oz can", case_size=12 [run_sql query result]
> - Production: One run (RUN-01349) existed but was **cancelled** [run_sql query result]
> - Warehouse inventory: All snapshots from 2026-09-07 through 2026-10-26 show **0 in_transit** for this SKU across all warehouses [run_sql query result]
> 
> **Who settles if records disagree:**
> According to the Escalation ownership policy [POL-04-v1#2], when "Two sources of data disagree", the owners of each source investigate and **Finance decides which is right**.

**Code checks:** pass

**Judge:** fail: The answer opens with "Yes" to whether the user can say the shipment definitely happened, which contradicts the reference conclusion that the conflicting production and inventory records do not justify saying so. It also cites zero in-transit stock instead of the zero on-hand stock the reference requires.


### 10. E19 (trap, disagreement)

**Question.** How many cases has Harlowmere ordered across the whole dataset?

**Reference answer.** Harlowmere is ambiguous: the data contains Harlowmere Beverage Co and Harlowmere Bev Supply. Ask which distributor is intended, or clearly report both separately: Harlowmere Beverage Co ordered 156,640 cases across 453 POs, and Harlowmere Bev Supply ordered 99,600 cases across 320 POs. Do not silently select one distributor or combine them into one account total. A clarification naming both distributors is a complete acceptable answer without the totals.

**Notes.** DP-04. No mandatory number check: clarification is as valid as separately labeled totals. The two full names must appear so ambiguity cannot be silently ignored.

**Agent answer (qwen/qwen3.5-9b):**

> Harlowmere has ordered 256,240 cases across the whole dataset.
> 
> The dataset contains two distributors with "Harlowmere" in their name—Harlowmere Bev Supply and Harlowmere Beverage Co—and together they account for 256,240 total cases.

**Code checks:** pass

**Judge:** fail: The answer names both distributors but combines them into a single total of 256,240 cases, which the reference explicitly forbids, instead of reporting separate totals or asking which one is meant.
