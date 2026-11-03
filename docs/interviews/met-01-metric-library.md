# Interview: MET-01 Metric library

Eric's answers, word for word (D27). `docs_corpus/met-01-metric-library.md` is drafted
from these answers only.

## Given during the POL-02 interview (2026-11-03)

> depletions = product moved out of the warehouse in any manner; sales, samples, spoiled, damaged, etc.
>
> Cover = have supply available. 30 days of cover means we should be able to fulfill the next 30 days of expected purchase orders

## Round 1 (2026-11-03)

Claude Code first listed what the tables hold: `distributor_orders` has ordered quantity,
requested date, status and last-changed date, but no shipped quantity and no actual ship
or delivery date; `warehouse_inventory` has weekly on-hand, allocated and in-transit;
`promo_calendar` has planned lift only.

**1. Cover, the supply side.** On-hand only, on-hand minus allocated, or on-hand minus allocated plus in-transit?
> on hand minus allocated or with POs awaiting to be picked up.

**2. Cover, the demand side.** Open POs, the average order rate over the last N weeks, or both? Weeks or days?
> average order rate calculated by change in ordering in last 90 days verse shipments previous year

**3. Depletions in this data.** Treat shipped and received POs as depletions, or say they cannot be measured yet?
> Depletions are on products out of the distributors warehouses.

**4. Fill rate.** What does it measure, over what period?
> Fill rate, yes shipped divided by ordered

**5. On-time-in-full.** What makes an order on time, and in full?
> strict. by requested date and in the total amoutn

**6. Lift.** Against which baseline? Is planned lift only, in v1, okay?
> vs same weeks last year

**7. Anything else** for the library?
> no

**8. Header.** Owner, and effective date (2026-10-01 unless Eric says otherwise).
> agreed

## Round 2 (2026-11-03)

Claude Code checked two readings (1: "allocated" means stock committed to POs awaiting
pickup, one subtraction; 2: expected POs are last year's shipments for the same period
times the recent trend), asked three gaps (how the 90-day change is measured, the fill
rate period, the owner), and listed what the data cannot support (no distributor
depletion data; no ship date or shipped quantity on POs; planned lift only).
> 1. no. Allocated and with POs issued and awaiting to be picked up are two different things. Allocated would be sitting in stock and allocated to a specific distributor for specifc accounts and the POs for that product hasn't been issued.
> 2. yes
>
> Gaps
>
> 1. yes
> 2. rolling 90
> 3. This is Product VP
>
> We should be getting depletion reports from distributors
> Shipments - fix that

## Sign-off (2026-11-03)

Claude Code showed the full text, noting three sentences of its own (the intro line,
"cover in weeks is cover in days divided by 7", "in-transit stock does not count"), and
asked whether to commit MET-01 as it reads.
> Commit it
