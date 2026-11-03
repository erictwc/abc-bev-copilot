DOC-ID: MET-01-v1
Title: Metric library
Owner: Product VP
Effective date: 2026-10-01

# Metric library

Definitions of the supply and trade metrics used in ABC-BEV-CO policies.

## Cover

Cover is how long the supply available can fill the expected purchase orders. 30 days of
cover means the supply available can fill the next 30 days of expected purchase orders.
Cover in weeks is cover in days divided by 7.

- **Supply available:** on-hand, minus stock that is allocated, minus stock on purchase
  orders that have been issued and are awaiting pickup. In-transit stock does not count.
- **Allocated:** stock sitting in the warehouse that is set aside for a specific
  distributor for specific accounts, before the purchase order for it has been issued.
  It is not the same as stock on an issued purchase order awaiting pickup.
- **Expected purchase orders:** last year's shipments for the same period, multiplied by
  the change in ordering: orders in the last 90 days divided by shipments in the same 90
  days a year earlier.

## Depletions

Depletions are product moved out of the distributors' warehouses in any manner: sales,
samples, spoiled, damaged and so on. Distributors send ABC-BEV-CO depletion reports.

## Fill rate

Fill rate is cases shipped divided by cases ordered, over a rolling 90 days.

## On-time-in-full (OTIF)

An order is on time and in full only if the total quantity ordered is delivered by the
requested date. There is no grace window and no tolerance on quantity.

## Lift

Lift is the percentage increase in units during a promo compared with the same weeks
last year.
