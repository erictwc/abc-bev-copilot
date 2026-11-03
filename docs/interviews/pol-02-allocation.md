# Interview: POL-02 Allocation policy

Eric's answers, word for word, given in a Claude Code session on 2026-11-03 (D27).
`docs_corpus/pol-02-allocation.md` is drafted from these answers only.

## Round 1

**1. When it starts.** What puts a SKU "on allocation"? For example: warehouse cover drops under some number of weeks, or a co-packer run is cut. Give the threshold if there is one. The sample question in the spec uses two weeks of cover.
> sounds good

**2. Who decides.** Who puts a SKU on allocation and takes it off, and who signs off on the split?
> starts with Production then goes to Portfolio, Sales has a chance to weigh in. commercial VP is the final arbitrator.

**3. Priority between SKU types.** How do promoted, launch and regular SKUs rank?
> if a promotion is running or about to that is priority, launch skus can get pushed easily. regular skus are ranked by popularity.

**4. Splitting between distributors.** How is a short SKU divided among distributors?
> Strategic accounts first, then distributors in order net profitiability.

**5. Between warehouses.** Can stock be moved between WH-EAST, WH-CENTRAL and WH-WEST? Who decides, and is there a limit?
> yes. Supply Planning

**6. Promos at risk.** If a promoted SKU has under the threshold of cover before the promo starts, what happens, and who makes the call?
> protect the promo but running out of a promo isn't the biggest problem, we SHOULD run out, that's the point of a promo, then we can build FOMO.

**7. Telling distributors.** How and when are distributors told, and can they appeal?
> When it happens. They can try

**8. Ending it.** When does a SKU come off allocation?
> When we have ample supply across the supply chain

**9. Header.** Owner and effective date (2026-10-01 if left to Claude Code).
> Product VP

## Round 2 (2026-11-03)

Claude Code checked its reading of question 1 (both triggers: cover under two weeks, and
a co-packer run being cut), then asked about six gaps, any limit on warehouse transfers,
and for a line-by-line read.
> you read "sounds good" right
>
> 1. 4 weeks
> 2. below regular. We can always push them
> 3. 6 months rolling depletions
> 4. More locations, more strategic
> 5. Sales and Portfolio likely hear complaints
> 6. 30 days cover

## Round 3 (2026-11-03)

Claude Code noted that "depletions" and "cover" need definitions in MET-01, and asked who
decides which distributors are strategic accounts and whether warehouse transfers have a
limit.
> depletions = product moved out of the warehouse in any manner; sales, samples, spoiled, damaged, etc.
>
> Cover = have supply available. 30 days of cover means we should be able to fulfill the next 30 days of expected purchase orders
>
> Its not distributors that are strategic, we're talking about final retailers being strategic. Distributors will each have them. We'll want to make sure they are keeping those strategic retailers in stock over other accounts
>
> 2. no

## Sign-off (2026-11-03)

Claude Code showed the full text and asked whether to commit POL-02 as it reads.
> Commit it
