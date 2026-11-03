# Data

The six v1 tables for ABC-BEV-CO, written by `data/generate.py` (tickets T1 and T2b). Everything
in them is invented.

This file is the **only** place the planted problems are described. The data carries
no flag column, note or comment that points at them, and it must stay that way: an
eval trap only means something if the agent has to notice the problem itself.

## How it is made

- `make data` writes `data/csv/*.csv` and `data/csv/SHA256SUMS`. Standard library only (D18).
- `make data-check` generates twice into temporary folders and confirms both runs and the
  committed `data/csv/` are byte-identical.
- Every date is counted from the anchor **2026-10-31**, the dataset's "today" (D19).
  "Next month" is November 2026.
- All randomness comes from two seeded streams: `random.Random(1031)` for the T1 tables,
  then `random.Random("1031:T2b")` for the T2b columns and table, used only after the T1
  rows are final. So T2b changed no T1 value: the four untouched tables are byte-identical
  to T1, and the first eight columns of `distributor_orders` are too (D29).
- CSV, not a DuckDB file, because a `.duckdb` file is not byte-identical between runs (D17).
  DuckDB loads these CSVs when the SQL tool is built (T5).
- Quantities are in cases. Empty CSV fields load as NULL.

## Tables

| Table | Rows | Columns | Notes |
|---|---:|---|---|
| `sku_master` | 40 | sku_id, brand, flavor, pack, case_size, copacker_line, status | 4 brands × 5 flavors × 2 packs. `status` is active, launch or discontinued. |
| `distributor_orders` | 4,647 | po_id, distributor, sku_id, qty, order_date, requested_date, status, last_changed, pickup_date, carrier, ship_date, shipped_qty, delivered_date | 12 distributors, orders placed Nov 2024 to Oct 2026. One SKU per PO line. Status: open, confirmed, shipped, received. The last five columns were added in T2b (see below). |
| `copacker_plan` | 1,514 | run_id, sku_id, planned_qty, scheduled_week, status, constraint_note | `scheduled_week` is a Monday. Status: completed, cancelled, confirmed, planned. Runs reach 9 weeks past the anchor. |
| `warehouse_inventory` | 11,694 | snapshot_date, warehouse, sku_id, on_hand, allocated, in_transit | Every Monday from 2024-11-04 to 2026-10-26, for WH-EAST, WH-CENTRAL and WH-WEST. |
| `promo_calendar` | 237 | retailer, chain, sku_id, start_date, end_date, authorized, planned_lift_pct, ad_week | `retailer` is the parent company and `chain` the store banner. 14-day promos starting on Mondays, through Dec 2026. `ad_week` is the ISO week of the start. |
| `distributor_depletions` | 19,829 | week_ending, distributor, sku_id, sold, samples, spoiled, damaged | T2b. Each distributor's weekly depletion report, by reason, in cases. `week_ending` is a Friday, 2024-11-15 to 2026-10-30. |

There is no `distributor` table and no promo ID, matching the column lists in `SPEC.md`.

### Shipments, pickups and depletions (T2b)

Added so the metric library (MET-01) and the PO change policy (POL-01) can be computed
(D30 to D33).

- `requested_date` is the requested **delivery** date; on-time-in-full is measured against it.
- `pickup_date` and `carrier` are filled in once a carrier is assigned, 1 to 4 days before
  the requested date. Carriers are codes, `CARRIER-1` to `CARRIER-4`. Open POs have
  neither; a confirmed PO gets them once its pickup is within 7 days of the anchor.
- **Awaiting pickup** is `status = 'confirmed'` with a `pickup_date` (D32): 25 POs, pickups
  2026-11-02 to 2026-11-07. The other 28 confirmed POs have no carrier yet.
- `ship_date` is the pickup date. `shipped_qty` is set on every shipped and received PO.
  228 received POs shipped short (`shipped_qty < qty`); the overall fill rate on shipped
  and received POs is 98.9%.
- `delivered_date` is set only on received POs, after `ship_date` and no later than
  `last_changed`. 238 received POs arrived after their requested date; 89.4% of received
  POs were on time and in full.
- Purchase orders have no warehouse column, so supply available (MET-01) is computed per
  SKU across the three warehouses: on-hand minus allocated, minus the quantity on POs
  awaiting pickup.
- `distributor_depletions` follows each distributor's own orders for the SKUs it carries,
  from its first requested delivery date onward. About 98% of the cases are `sold`;
  `samples`, `spoiled` and `damaged` make up the rest. Discontinued SKUs stop 8 weeks after 2025-12-31. A SKU
  with no completed co-packer run has no depletions.
Distributors are plain name strings.

## Planted problems

The queries are DuckDB SQL, written against tables named as above (for example
`create view promo_calendar as select * from read_csv('data/csv/promo_calendar.csv')`).
Each one returns the planted rows. The row excerpts come from the committed data at
the hashes in `data/csv/SHA256SUMS`.

### DP-01. One SKU spelled two ways in two tables

- **Where:** `promo_calendar`, all 10 promo rows for one SKU.
- **What:** `sku_master` has `TRV-KIW-C12` (Torvane, Frost Kiwi, 12 oz can).
  `promo_calendar` spells it `TRV-KIWI-C12`, with the flavor word written out in full.
  A join on `sku_id` silently drops every promo for this SKU, including the November
  2026 one (Stonefinch Fuel Stop, 2026-11-30 to 2026-12-13, authorized `y`). A
  "which promoted SKUs next month..." question that joins the tables misses it.
- **Trap it supports:** misspelled SKU.

```sql
select p.sku_id, count(*) as promos, max(p.start_date) as latest_start
from promo_calendar p
where p.sku_id not in (select sku_id from sku_master)
group by 1;
-- TRV-KIWI-C12 | 10 | 2026-11-30
```

### DP-02. One month of missing data in one table

- **Where:** `distributor_orders`.
- **What:** no PO has an `order_date` in **June 2025**, for any distributor. The months on
  either side have about 200 POs each. POs ordered in May 2025 still show June
  `requested_date`s, as real data would. PO numbers run on without a gap, because they
  are assigned after the gap. A total that reads June 2025 as "zero demand" is wrong:
  the data is missing, not the orders. `distributor_depletions` has no gap in June 2025
  (812 weekly rows), so the distributors kept selling.
- **Trap it supports:** missing-month data problem.

```sql
select strftime(m, '%Y-%m') as missing_month
from (select unnest(generate_series(date '2024-11-01', date '2026-10-01', interval 1 month)) as m)
where m not in (select date_trunc('month', order_date) from distributor_orders);
-- 2025-06
```

### DP-03. A PO whose status contradicts the co-packer plan

- **Where:** `distributor_orders` PO-004395, against `copacker_plan` RUN-01349.
- **What:** `SKX-PSF-C16` (Skerrix, Gale Passionfruit, 16 oz can) is a launch SKU. Its
  only production run, RUN-01349 in the week of 2026-10-05, is `cancelled` ("Line
  maintenance"). The SKU has zero on hand, allocated and in transit in all 24 of its
  inventory snapshots. Yet PO-004395 (Brindlecross Beverage, 310 cases, requested
  2026-10-16) is `shipped`, last changed 2026-10-14, so product that was never made
  shipped. The other 13 POs for this SKU are `open`. The link is SKU plus timing; there
  is no PO-to-run key in the schema. Since T2b the PO carries a full shipment record
  (pickup and ship date 2026-10-14, CARRIER-3, `shipped_qty` 310, no delivery yet), and
  `distributor_depletions` has no rows for the SKU at all.
- **Trap it supports:** contradictory PO status.

```sql
select o.po_id, o.distributor, o.status, o.requested_date, r.run_id, r.scheduled_week, r.status as run_status
from distributor_orders o
join copacker_plan r using (sku_id)
where o.status in ('shipped', 'received')
  and o.sku_id not in (select sku_id from copacker_plan where status = 'completed');
-- PO-004395 | Brindlecross Beverage | shipped | 2026-10-16 | RUN-01349 | 2026-10-05 | cancelled
```

### DP-04. Ambiguous distributor name

- **Where:** `distributor_orders.distributor`.
- **What:** two distributors share the prefix "Harlowmere": **Harlowmere Beverage Co**
  (453 POs) and **Harlowmere Bev Supply** (320 POs). Both order across the full 24
  months. A question about "Harlowmere" is ambiguous: the agent should ask, or answer
  for both and say so, not pick one or add them up silently.
- **Trap it supports:** ambiguous distributor.

```sql
select distributor, count(*) as pos
from distributor_orders
where distributor like 'Harlowmere%'
group by 1;
-- Harlowmere Beverage Co | 453
-- Harlowmere Bev Supply  | 320
```

### DP-05. A promo with no authorization flag

- **Where:** `promo_calendar`, one row.
- **What:** Corvane Retail Group / Corvane Market, `QLB-MNG-C16` (Quillbolt, Static Mango,
  16 oz can), 2026-11-09 to 2026-11-22, ad week 2026-W46, planned lift 14%. `authorized`
  is empty (NULL), neither `y` nor `n`. A filter on `authorized = 'y'` or `= 'n'` misses
  it. The honest answer is "authorization not recorded", which the promo authorization
  procedure (T2) should say how to handle.
- **Trap it supports:** missing authorization (no named trap in the spec yet; available for
  the combined cases).

```sql
select * from promo_calendar where authorized is null;
-- Corvane Retail Group | Corvane Market | QLB-MNG-C16 | 2026-11-09 | 2026-11-22 | NULL | 14 | 2026-W46
```

### Checked absent: no accidental problems

When T1 was built, the same queries also confirmed there is nothing beyond the five:
every `sku_id` in the other four tables exists in `sku_master` except DP-01's; only
June 2025 is missing; only PO-004395 is shipped or received without a completed run;
only "Harlowmere" is a shared first word among distributors; only one `authorized` is
NULL. There are also no duplicate runs per SKU and week, no orders for discontinued SKUs
after 2025-12-31, and no `last_changed` before `order_date`.

When T2b was built, the same checks were repeated on the new columns and table: every
`sku_id` in `distributor_depletions` exists in `sku_master`; every `week_ending` is a
Friday; no depletion is negative; no `ship_date` is after the anchor; no `pickup_date` is
before `order_date`; every `delivered_date` is after `ship_date` and no later than
`last_changed`; `shipped_qty` never exceeds `qty`. These were checked with a Python
script, not yet as DuckDB SQL.

## Name check

Every brand, flavor, distributor, retailer and chain name was invented, then
searched on the web (on 2026-11-02) as an exact phrase with beverage, drink,
distributor or store context.

- **No name in use matched a real beverage business.**
- **Replaced as a precaution:** three flavor candidates, each for a close
  resemblance: one is an existing supplement flavor, one shares a word with a real
  energy-drink brand, and one is near a real cider. The real names are left out on
  purpose.
- **Non-beverage uses (allowed under D16):** "Torvane" is a soil-testing instrument;
  "Lumaro" is a lighting product line.

Web search shows only that no evidence was found; it is not a trademark search.

| Kind | Names |
|---|---|
| Brands | Quillbolt (QLB), Torvane (TRV), Lumaro (LMR), Skerrix (SKX) |
| Flavors | Static Mango, Comet Cranberry, Glacier Plum, Spark Tangerine, Thunder Guava, Midnight Yuzu, Copper Peach, Frost Kiwi, Solar Grape, Velvet Cherry, Neon Pear, Cinder Berry, Tidal Melon, Prism Punch, Quartz Lemon, Dusk Papaya, Flint Apple, Arc Pineapple, Mist Lychee, Gale Passionfruit |
| Distributors | Harlowmere Beverage Co, Harlowmere Bev Supply, Ostrander Valley Distributing, Calderwick Distribution, Penmoor Beverage, Thistlecombe Distributing, Rookhaven Beverage, Marrowfield Distributors, Ellisdane Beverage, Quarrytown Distributing, Brindlecross Beverage, Fenwhistle Distributing |
| Retailers / chains | Corvane Retail Group (Corvane Market, Corvane Express), Pellweather Holdings (Pellweather Foods), Stonefinch Inc (Stonefinch Fuel Stop, Stonefinch Grocer), Mirelle Co (Mirelle Mart) |

The co-packer is unnamed; its lines are LINE-1 to LINE-3. Warehouses are codes only.
