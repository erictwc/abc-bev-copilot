"""Product sheet generator and corpus header check (ticket T2).

Writes one Markdown sheet per flavor (both packs on each) from
data/csv/sku_master.csv to --out (default docs_corpus). Standard library only.
Same input, byte-identical files (D23):

- the invented specs (caffeine, calories, sugar, shelf life) come from one
  random.Random(SEED), drawn in sku_master order (D24)
- integer arithmetic only; line endings are "\\n"

Sheets cite only sku_master IDs and say nothing about runs, POs or promos, so
they cannot hint at the planted data problems in docs/DATA.md.

--check validates the whole corpus instead: every docs_corpus/*.md except
README.md has the four-line header (D22), the count is 20 to 30, and every
SKU-shaped token in the corpus exists in sku_master. Stubs are listed as pending.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent
SKU_MASTER = ROOT / "data" / "csv" / "sku_master.csv"
CORPUS = ROOT / "docs_corpus"
SEED = 1031
VERSION = "v1"
OWNER = "Brand Management"
EFFECTIVE = "2026-10-01"

CAFFEINE_MG_PER_OZ = {"QLB": 10, "TRV": 9, "LMR": 8, "SKX": 12}   # brand-level, so packs scale by size
CALORIES_12OZ = [10, 15, 110, 140, 160]      # 10 and 15 are the zero-sugar recipes
SHELF_LIFE_MONTHS = [9, 12, 12, 15]
STATUS_TEXT = {
    "active": "in regular distribution",
    "launch": "newly introduced item",
    "discontinued": "no longer produced",
}
HEADER_KEYS = ["DOC-ID", "Title", "Owner", "Effective date"]
SKU_TOKEN = re.compile(r"\b[A-Z]{3}-[A-Z]{3,}-C\d{2}\b")


def read_skus():
    with open(SKU_MASTER, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pack_oz(sku):
    return int(sku["pack"].split()[0])


def make_specs(rng, skus):
    """Per-flavor recipe and per-brand shelf life, drawn in sku_master order."""
    recipes, shelf = {}, {}
    for s in skus:
        brand, flavor = s["sku_id"].split("-")[:2]
        if brand not in shelf:
            shelf[brand] = rng.choice(SHELF_LIFE_MONTHS)
        if (brand, flavor) not in recipes:
            recipes[(brand, flavor)] = rng.choice(CALORIES_12OZ)
    return recipes, shelf


def sheet(brand_code, flavor_code, packs, cal12, shelf_months):
    first = packs[0]
    title = f"{first['brand']} {first['flavor']} product sheet"
    zero = cal12 <= 15
    lines = [
        f"DOC-ID: PRD-{brand_code}-{flavor_code}-{VERSION}",
        f"Title: {title}",
        f"Owner: {OWNER}",
        f"Effective date: {EFFECTIVE}",
        "",
        f"# {first['brand']} {first['flavor']}",
        "",
        f"{first['brand']} {first['flavor']} is {'a zero-sugar' if zero else 'an'} energy drink "
        f"made for ABC-BEV-CO on co-packer line {first['copacker_line']}. "
        f"It comes in {len(packs)} packs.",
        "",
        "## Packs",
        "",
        "| sku_id | Pack | Cans per case | Status |",
        "|---|---|---:|---|",
    ]
    for p in packs:
        lines.append(f"| {p['sku_id']} | {p['pack']} | {p['case_size']} | {p['status']} |")
    lines += [
        "",
        "## Caffeine and nutrition (per can)",
        "",
        "| sku_id | Caffeine (mg) | Calories | Sugar (g) |",
        "|---|---:|---:|---:|",
    ]
    for p in packs:
        oz = pack_oz(p)
        cal = (cal12 * oz + 6) // 12
        sugar = 0 if zero else cal // 4
        lines.append(f"| {p['sku_id']} | {CAFFEINE_MG_PER_OZ[brand_code] * oz} | {cal} | {sugar} |")
    lines += [
        "",
        "## Shelf life and storage",
        "",
        f"Shelf life is {shelf_months} months from the production date printed on the can. "
        "Store cases dry, out of direct sun, between 35 and 85 °F. Do not freeze.",
        "",
        "## Status",
        "",
    ]
    for status in sorted({p["status"] for p in packs}):
        ids = ", ".join(p["sku_id"] for p in packs if p["status"] == status)
        lines.append(f"- {status}: {STATUS_TEXT[status]} ({ids}).")
    slug = f"prd-{brand_code}-{flavor_code}".lower()
    return f"{slug}-{first['flavor'].lower().replace(' ', '-')}.md", "\n".join(lines) + "\n"


def generate(out):
    skus = read_skus()
    recipes, shelf = make_specs(Random(SEED), skus)
    groups = {}
    for s in skus:   # dicts keep insertion order, so sheets follow sku_master order
        groups.setdefault(tuple(s["sku_id"].split("-")[:2]), []).append(s)
    out.mkdir(parents=True, exist_ok=True)
    for (b, f), packs in groups.items():
        name, text = sheet(b, f, packs, recipes[(b, f)], shelf[b])
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(groups)} product sheets to {out}")


def check():
    known = {s["sku_id"] for s in read_skus()}
    files = sorted(p for p in CORPUS.glob("*.md") if p.name != "README.md")
    problems, ids = [], {}
    for p in files:
        head = p.read_text(encoding="utf-8").split("\n")
        for i, key in enumerate(HEADER_KEYS):
            line = head[i] if i < len(head) else ""
            if not line.startswith(f"{key}: ") or not line[len(key) + 2:].strip():
                problems.append(f"{p.name}: line {i + 1} should be '{key}: <value>'")
        if len(head) < 5 or head[4] != "":
            problems.append(f"{p.name}: line 5 should be blank")
        doc_id = head[0][len("DOC-ID: "):]
        if not re.fullmatch(r"[A-Z]{3}(-[A-Z0-9]+)+-v\d+", doc_id):
            problems.append(f"{p.name}: DOC-ID '{doc_id}' does not end in a version like -v1")
        ids.setdefault(doc_id, []).append(p.name)
        if len(head) > 3 and ("TBD" in head[2] + head[3] or any(m in "\n".join(head[4:]) for m in ("Draft pending", "[GAP"))):
            print(f"pending: {p.name} is not finished (TBD header, Draft pending body or [GAP] marker)")
        for tok in sorted(set(SKU_TOKEN.findall(p.read_text(encoding="utf-8"))) - known):
            problems.append(f"{p.name}: '{tok}' is not a sku_master sku_id")
    problems += [f"duplicate DOC-ID {k}: {v}" for k, v in ids.items() if len(v) > 1]
    if not 20 <= len(files) <= 30:
        problems.append(f"corpus has {len(files)} files, needs 20 to 30")
    for msg in problems:
        print(f"FAIL {msg}")
    print(f"corpus-check: {len(files)} files, {len(problems)} problems")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=CORPUS)
    ap.add_argument("--check", action="store_true", help="validate headers and count of the corpus")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    generate(args.out)


if __name__ == "__main__":
    main()
