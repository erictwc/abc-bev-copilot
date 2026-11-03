"""Seeded generator for the six v1 tables (tickets T1 and T2b).

Writes CSV files plus SHA256SUMS to --out (default data/csv). Standard library
only (D18). Same seed, byte-identical files (D17):

- every date is counted from ANCHOR, never from today's date (D19)
- all randomness comes from two random.Random streams fixed by the seed, passed
  down explicitly: the T1 stream, then a second one for the T2b columns and table,
  used only after the T1 rows are final, so T2b leaves every T1 value unchanged (D29)
- only rng.random(), randrange(), choice() and sample() are used, and no libm
  functions (exp, log, sin...), whose last bit can differ between platforms
- no iteration over sets: string hashing is randomized per process
- rows are sorted before writing; line endings are "\\n"; numbers are integers

The deliberate data problems are described in docs/DATA.md and nowhere else.
"""

import argparse
import csv
import hashlib
from datetime import date, timedelta
from pathlib import Path
from random import Random

ANCHOR = date(2026, 10, 31)   # the dataset's "today" (D19)
SEED = 1031
MONTHS = 24                   # order history: Nov 2024 .. Oct 2026
START = date(2024, 11, 1)
HORIZON = ANCHOR + timedelta(weeks=9)   # plans and promos reach past the anchor

# All names are invented and were checked against real beverage businesses (docs/DATA.md).
BRANDS = [  # brand, code, [(flavor, code, full word)]
    ("Quillbolt", "QLB", [("Static Mango", "MNG", "MANGO"), ("Comet Cranberry", "CRN", "CRANBERRY"),
                          ("Glacier Plum", "PLM", "PLUM"), ("Spark Tangerine", "TNG", "TANGERINE"),
                          ("Thunder Guava", "GUA", "GUAVA")]),
    ("Torvane", "TRV", [("Midnight Yuzu", "YUZ", "YUZU"), ("Copper Peach", "PCH", "PEACH"),
                        ("Frost Kiwi", "KIW", "KIWI"), ("Solar Grape", "GRP", "GRAPE"),
                        ("Velvet Cherry", "CHR", "CHERRY")]),
    ("Lumaro", "LMR", [("Neon Pear", "PEA", "PEAR"), ("Cinder Berry", "BRY", "BERRY"),
                       ("Tidal Melon", "MEL", "MELON"), ("Prism Punch", "PUN", "PUNCH"),
                       ("Quartz Lemon", "LEM", "LEMON")]),
    ("Skerrix", "SKX", [("Dusk Papaya", "PAP", "PAPAYA"), ("Flint Apple", "APL", "APPLE"),
                        ("Arc Pineapple", "PIN", "PINEAPPLE"), ("Mist Lychee", "LYC", "LYCHEE"),
                        ("Gale Passionfruit", "PSF", "PASSIONFRUIT")]),
]
PACKS = [("C12", "12 oz can", 24), ("C16", "16 oz can", 12)]
LINES = {"QLB": "LINE-1", "TRV": "LINE-2", "LMR": "LINE-3", "SKX": "LINE-3"}
LAUNCH = date(2026, 9, 7)
LAUNCH_SKUS = ["TRV-YUZ-C16", "SKX-PSF-C16"]
DISCONTINUED = date(2025, 12, 31)
DISCONTINUED_SKUS = ["LMR-PUN-C12", "LMR-PUN-C16"]

DISTRIBUTORS = [
    "Harlowmere Beverage Co", "Harlowmere Bev Supply", "Ostrander Valley Distributing",
    "Calderwick Distribution", "Penmoor Beverage", "Thistlecombe Distributing",
    "Rookhaven Beverage", "Marrowfield Distributors", "Ellisdane Beverage",
    "Quarrytown Distributing", "Brindlecross Beverage", "Fenwhistle Distributing",
]
CHAINS = [  # retailer (parent company), chain (store banner)
    ("Corvane Retail Group", "Corvane Market"), ("Corvane Retail Group", "Corvane Express"),
    ("Pellweather Holdings", "Pellweather Foods"), ("Stonefinch Inc", "Stonefinch Fuel Stop"),
    ("Stonefinch Inc", "Stonefinch Grocer"), ("Mirelle Co", "Mirelle Mart"),
]
WAREHOUSES = [("WH-EAST", 4), ("WH-CENTRAL", 3), ("WH-WEST", 3)]   # name, demand weight
CARRIERS = ["CARRIER-1", "CARRIER-2", "CARRIER-3", "CARRIER-4"]   # codes, not names (D33)
CARRIER_LEAD = timedelta(days=7)   # a carrier is assigned this close to pickup (POL-01)
RUN_NOTES = ["Can supplier short", "Line maintenance", "Flavor concentrate late",
             "Changeover overran", "Labor shortage on shift"]

MISSING_MONTH = (2025, 6)   # docs/DATA.md DP-02


def uniform(rng, lo, hi):
    return lo + (hi - lo) * rng.random()


def mondays(first, last):
    d = first + timedelta(days=(7 - first.weekday()) % 7)
    while d <= last:
        yield d
        d += timedelta(weeks=1)


def month_starts():
    y, m = START.year, START.month
    for _ in range(MONTHS + 2):   # two months past the anchor, for promos
        yield date(y, m, 1)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def days_in_month(d):
    nxt = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return (nxt - d).days


def sellable(sku, d):
    if sku["sku_id"] in LAUNCH_SKUS:
        return d >= LAUNCH
    if sku["sku_id"] in DISCONTINUED_SKUS:
        return d <= DISCONTINUED
    return True


def make_skus(rng):
    skus = []
    for brand, bcode, flavors in BRANDS:
        for flavor, fcode, _ in flavors:
            for pcode, pack, case_size in PACKS:
                sku_id = f"{bcode}-{fcode}-{pcode}"
                status = ("launch" if sku_id in LAUNCH_SKUS else
                          "discontinued" if sku_id in DISCONTINUED_SKUS else "active")
                skus.append({"sku_id": sku_id, "brand": brand, "flavor": flavor, "pack": pack,
                             "case_size": case_size, "copacker_line": LINES[bcode], "status": status,
                             "weekly_cases": rng.randrange(150, 1500, 10)})
    return skus


def make_orders(rng, skus):
    rows = []
    for dist in DISTRIBUTORS:
        carried = rng.sample(skus, rng.randrange(14, 26))
        carried.sort(key=lambda s: s["sku_id"])
        share = uniform(rng, 0.04, 0.12)
        for month in month_starts():
            for sku in carried:
                for _ in range(1 + (rng.random() < 0.2)):
                    order_date = month + timedelta(days=rng.randrange(days_in_month(month)))
                    if rng.random() > 0.85 or order_date > ANCHOR or not sellable(sku, order_date):
                        continue
                    requested = order_date + timedelta(days=rng.randrange(10, 29))
                    qty = max(10, round(sku["weekly_cases"] * 4 * share * uniform(rng, 0.7, 1.3) / 10) * 10)
                    if requested <= ANCHOR - timedelta(days=10):
                        status = "received" if rng.random() < 0.97 else "shipped"
                        changed = requested + timedelta(days=rng.randrange(0, 4))
                    elif requested <= ANCHOR + timedelta(days=5):
                        status = "shipped"
                        changed = min(ANCHOR, requested - timedelta(days=rng.randrange(1, 4)))
                    elif order_date <= ANCHOR - timedelta(days=5):
                        status = "confirmed"
                        changed = order_date + timedelta(days=rng.randrange(1, 5))
                    else:
                        status = "open"
                        changed = order_date
                    rows.append({"distributor": dist, "sku_id": sku["sku_id"], "qty": qty,
                                 "order_date": order_date, "requested_date": requested,
                                 "status": status, "last_changed": min(changed, ANCHOR)})
    return rows


def make_runs(rng, skus):
    rows = []
    for sku in skus:
        if sku["sku_id"] in LAUNCH_SKUS:
            continue   # launch runs are placed below
        every = rng.randrange(2, 5)
        weeks = list(mondays(START, HORIZON))
        for week in weeks[rng.randrange(every)::every]:
            if not sellable(sku, week):
                continue
            rows.append(run_row(rng, sku, week, every))
    launch = next(s for s in skus if s["sku_id"] == LAUNCH_SKUS[0])
    rows.append(run_row(rng, launch, LAUNCH - timedelta(weeks=1), 3, status="completed"))
    for week in list(mondays(LAUNCH + timedelta(weeks=2), HORIZON))[::3]:
        rows.append(run_row(rng, launch, week, 3))
    return rows


def run_row(rng, sku, week, every, status=None):
    qty = round(sku["weekly_cases"] * every * uniform(rng, 0.9, 1.1) / 100) * 100
    note = ""
    if status is None:
        if week + timedelta(days=6) < ANCHOR:
            status = "completed" if rng.random() < 0.94 else "cancelled"
        else:
            status = "confirmed" if week <= ANCHOR + timedelta(weeks=3) else "planned"
        if status == "cancelled" or rng.random() < 0.05:
            note = rng.choice(RUN_NOTES)
    return {"sku_id": sku["sku_id"], "planned_qty": qty, "scheduled_week": week,
            "status": status, "constraint_note": note}


def make_inventory(rng, skus):
    rows = []
    for sku in skus:
        for wh, weight in WAREHOUSES:
            demand = sku["weekly_cases"] * weight / 10
            cover = uniform(rng, 2, 5)
            for snap in mondays(START, ANCHOR):
                cover = min(7.0, max(0.4, cover + uniform(rng, -0.8, 0.8)))
                if sku["sku_id"] in LAUNCH_SKUS and snap < LAUNCH:
                    continue
                if sku["sku_id"] in DISCONTINUED_SKUS and snap > DISCONTINUED + timedelta(weeks=8):
                    continue
                on_hand = round(demand * cover)
                if sku["sku_id"] in DISCONTINUED_SKUS and snap > DISCONTINUED:
                    on_hand = round(on_hand * (1 - (snap - DISCONTINUED).days / 63))
                allocated = round(on_hand * uniform(rng, 0.1, 0.5))
                in_transit = round(demand * uniform(rng, 0, 1.5))
                rows.append({"snapshot_date": snap, "warehouse": wh, "sku_id": sku["sku_id"],
                             "on_hand": on_hand, "allocated": allocated, "in_transit": in_transit})
    return rows


def make_promos(rng, skus):
    rows, seen = [], []
    for retailer, chain in CHAINS:
        for month in month_starts():
            for _ in range(1 + (rng.random() < 0.5)):
                start = month + timedelta(days=rng.randrange(days_in_month(month)))
                start -= timedelta(days=start.weekday())   # promos start on a Monday
                choices = [s for s in skus if sellable(s, start) and sellable(s, start + timedelta(days=13))]
                sku = rng.choice(choices)
                future = start > ANCHOR
                authorized = "y" if rng.random() < (0.7 if future else 0.92) else "n"
                lift = rng.randrange(10, 46)
                key = (chain, sku["sku_id"], start)
                if key in seen or start < START:
                    continue
                seen.append(key)
                iso = start.isocalendar()
                rows.append({"retailer": retailer, "chain": chain, "sku_id": sku["sku_id"],
                             "start_date": start, "end_date": start + timedelta(days=13),
                             "authorized": authorized, "planned_lift_pct": lift,
                             "ad_week": f"{iso[0]}-W{iso[1]:02d}"})
    return rows


def plant(rng, skus, orders, runs, inventory, promos):
    """The five deliberate problems. Each is described in docs/DATA.md (DP-01..DP-05)."""
    # DP-01: one promoted SKU is spelled with its full flavor word in promo_calendar.
    nov = sorted((p for p in promos if p["start_date"].year == 2026 and p["start_date"].month == 11),
                 key=lambda p: (p["start_date"], p["chain"], p["sku_id"]))
    active = sorted({p["sku_id"] for p in nov if p["sku_id"] not in LAUNCH_SKUS})
    dp01 = rng.choice(active)
    full = {f"{b}-{f}": word for _, b, fl in BRANDS for _, f, word in fl}
    prefix, pack = dp01.rsplit("-", 1)
    variant = f"{prefix.split('-')[0]}-{full[prefix]}-{pack}"
    for p in promos:
        if p["sku_id"] == dp01:
            p["sku_id"] = variant
    # DP-02: no distributor orders placed in one month.
    orders[:] = [o for o in orders if (o["order_date"].year, o["order_date"].month) != MISSING_MONTH]
    # DP-03: the second launch SKU's only run is cancelled, yet one of its POs shipped.
    dp03, week = LAUNCH_SKUS[1], date(2026, 10, 5)
    runs.append({"sku_id": dp03, "planned_qty": 4800, "scheduled_week": week,
                 "status": "cancelled", "constraint_note": rng.choice(RUN_NOTES)})
    for inv in inventory:
        if inv["sku_id"] == dp03:
            inv["on_hand"] = inv["allocated"] = inv["in_transit"] = 0
    dp03_pos = sorted((o for o in orders if o["sku_id"] == dp03),
                      key=lambda o: (o["order_date"], o["distributor"]))
    for o in dp03_pos:
        o["status"], o["last_changed"] = "open", o["order_date"]
    shipped = rng.choice([o for o in dp03_pos if week + timedelta(weeks=1) <= o["requested_date"] <= ANCHOR])
    shipped["status"], shipped["last_changed"] = "shipped", shipped["requested_date"] - timedelta(days=2)
    # DP-04 needs no change: two of DISTRIBUTORS share the prefix "Harlowmere".
    # DP-05: one November promo has no authorization value at all.
    target = rng.choice([p for p in nov if p["sku_id"] not in (variant, dp01)])
    target["authorized"] = ""


def add_shipments(rng, orders):
    """T2b: pickup, carrier and shipment fields on every PO (D31). Awaiting pickup is
    status confirmed with a pickup date (D32). requested_date is the delivery date."""
    for o in orders:   # in po_id order
        o.update(pickup_date="", carrier="", ship_date="", shipped_qty="", delivered_date="")
        transit = timedelta(days=rng.randrange(1, 5))
        pickup = o["requested_date"] - transit
        if o["status"] == "shipped" and o["last_changed"] < o["requested_date"]:
            pickup = o["last_changed"]   # the status changed when the truck left
        if o["status"] == "confirmed" and pickup > ANCHOR + CARRIER_LEAD:
            continue   # no carrier yet, so no pickup date
        if o["status"] == "open":
            continue
        o["pickup_date"], o["carrier"] = pickup, rng.choice(CARRIERS)
        if o["status"] == "confirmed":
            continue
        o["ship_date"], o["shipped_qty"] = pickup, o["qty"]
        if o["status"] == "received":
            if rng.random() < 0.05:   # short shipment
                o["shipped_qty"] = min(o["qty"] - 10, max(10, round(o["qty"] * uniform(rng, 0.6, 0.95) / 10) * 10))
            if rng.random() < 0.92:
                delivered = o["requested_date"] - timedelta(days=rng.randrange(transit.days))
            else:
                delivered = o["requested_date"] + timedelta(days=rng.randrange(1, 4))
            o["delivered_date"] = max(pickup + timedelta(days=1), min(delivered, o["last_changed"]))


def make_depletions(rng, orders, runs):
    """T2b: weekly distributor depletion reports, by reason (D30). Volumes follow each
    distributor's own orders. A SKU never produced has nothing to deplete."""
    made = {r["sku_id"] for r in runs if r["status"] == "completed"}
    lines = {}
    for o in orders:
        if o["sku_id"] in made:
            lines.setdefault((o["distributor"], o["sku_id"]), []).append(o)
    fridays = [m + timedelta(days=4) for m in mondays(START, ANCHOR - timedelta(days=4))]
    rows = []
    for (dist, sku_id), pos in sorted(lines.items()):
        first = min(o["requested_date"] for o in pos)   # depletions start once stock arrives
        last = DISCONTINUED + timedelta(weeks=8) if sku_id in DISCONTINUED_SKUS else ANCHOR
        weeks = (max(o["order_date"] for o in pos) - min(o["order_date"] for o in pos)).days / 7 + 4
        weekly = sum(o["qty"] for o in pos) / weeks
        for fri in fridays:
            if fri < first or fri > last:
                continue
            total = max(0, round(weekly * uniform(rng, 0.75, 1.25)))
            samples = round(total * uniform(rng, 0.005, 0.02))
            spoiled = round(total * uniform(rng, 0, 0.01))
            damaged = round(total * uniform(rng, 0, 0.01))
            rows.append({"week_ending": fri, "distributor": dist, "sku_id": sku_id,
                         "sold": total - samples - spoiled - damaged, "samples": samples,
                         "spoiled": spoiled, "damaged": damaged})
    rows.sort(key=lambda d: (d["week_ending"], d["distributor"], d["sku_id"]))
    return rows


def write(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c].isoformat() if isinstance(r[c], date) else r[c] for c in cols])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path(__file__).parent / "csv"))
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    rng = Random(args.seed)

    skus = make_skus(rng)
    orders = make_orders(rng, skus)
    runs = make_runs(rng, skus)
    inventory = make_inventory(rng, skus)
    promos = make_promos(rng, skus)
    plant(rng, skus, orders, runs, inventory, promos)

    orders.sort(key=lambda o: (o["order_date"], o["distributor"], o["sku_id"], o["requested_date"]))
    for i, o in enumerate(orders, 1):
        o["po_id"] = f"PO-{i:06d}"
    runs.sort(key=lambda r: (r["scheduled_week"], r["sku_id"]))
    for i, r in enumerate(runs, 1):
        r["run_id"] = f"RUN-{i:05d}"
    inventory.sort(key=lambda v: (v["snapshot_date"], v["warehouse"], v["sku_id"]))
    promos.sort(key=lambda p: (p["start_date"], p["chain"], p["sku_id"]))

    rng2 = Random(f"{args.seed}:T2b")   # second stream, after the T1 rows are final (D29)
    add_shipments(rng2, orders)
    depletions = make_depletions(rng2, orders, runs)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tables = {
        "sku_master": (skus, ["sku_id", "brand", "flavor", "pack", "case_size", "copacker_line", "status"]),
        "distributor_orders": (orders, ["po_id", "distributor", "sku_id", "qty", "order_date",
                                        "requested_date", "status", "last_changed", "pickup_date",
                                        "carrier", "ship_date", "shipped_qty", "delivered_date"]),
        "copacker_plan": (runs, ["run_id", "sku_id", "planned_qty", "scheduled_week", "status",
                                 "constraint_note"]),
        "warehouse_inventory": (inventory, ["snapshot_date", "warehouse", "sku_id", "on_hand",
                                            "allocated", "in_transit"]),
        "promo_calendar": (promos, ["retailer", "chain", "sku_id", "start_date", "end_date",
                                    "authorized", "planned_lift_pct", "ad_week"]),
        "distributor_depletions": (depletions, ["week_ending", "distributor", "sku_id", "sold",
                                                "samples", "spoiled", "damaged"]),
    }
    sums = []
    for name, (rows, cols) in tables.items():
        path = out / f"{name}.csv"
        write(path, rows, cols)
        sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
        print(f"{name:20} {len(rows):6} rows")
    (out / "SHA256SUMS").write_text("".join(sorted(sums, key=lambda s: s.split()[1])), encoding="utf-8")


if __name__ == "__main__":
    main()
