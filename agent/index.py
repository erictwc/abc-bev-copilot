"""Builds the two DuckDB files the tools read (T5). Both are gitignored build products (D17).

  python -m agent.index db      data/abc.duckdb: the six v1 tables from data/csv/, explicit types (D55)
  python -m agent.index docs    data/docs.duckdb: corpus chunks and their embeddings (D48-D50)

Chunking (D50): each document's body is split at its `##` headings, neighbouring sections are
merged while the result stays within chunk_chars, with no overlap. Chunks are numbered from 1
inside each document, so a passage is cited as `<DOC-ID>#<n>`. The text that is embedded starts
with the document title and the section headings; the text that is stored and returned does not.
"""
import argparse, re, sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from agent import tools

CSV_DIR = tools.ROOT / "data" / "csv"
CORPUS = tools.ROOT / "docs_corpus"

# Column order matches the CSV headers (docs/DATA.md). Flags and codes stay VARCHAR so an
# empty field loads as NULL rather than being guessed into another type (DP-05).
SCHEMA = {
    "sku_master": "sku_id VARCHAR, brand VARCHAR, flavor VARCHAR, pack VARCHAR, case_size INTEGER, "
                  "copacker_line VARCHAR, status VARCHAR",
    "distributor_orders": "po_id VARCHAR, distributor VARCHAR, sku_id VARCHAR, qty INTEGER, order_date DATE, "
                          "requested_date DATE, status VARCHAR, last_changed DATE, pickup_date DATE, "
                          "carrier VARCHAR, ship_date DATE, shipped_qty INTEGER, delivered_date DATE",
    "copacker_plan": "run_id VARCHAR, sku_id VARCHAR, planned_qty INTEGER, scheduled_week DATE, status VARCHAR, "
                     "constraint_note VARCHAR",
    "warehouse_inventory": "snapshot_date DATE, warehouse VARCHAR, sku_id VARCHAR, on_hand INTEGER, "
                           "allocated INTEGER, in_transit INTEGER",
    "promo_calendar": "retailer VARCHAR, chain VARCHAR, sku_id VARCHAR, start_date DATE, end_date DATE, "
                      "authorized VARCHAR, planned_lift_pct INTEGER, ad_week VARCHAR",
    "distributor_depletions": "week_ending DATE, distributor VARCHAR, sku_id VARCHAR, sold INTEGER, "
                              "samples INTEGER, spoiled INTEGER, damaged INTEGER",
}
assert tuple(SCHEMA) == tools.ALLOWED


def fresh(path):
    """Build into a temporary file and rename at the end, so a failed build leaves no half file."""
    tmp = path.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    return tmp


def build_db(out=tools.TABLES_DB):
    tmp = fresh(out)
    con = duckdb.connect(str(tmp))
    for table, columns in SCHEMA.items():
        header = (CSV_DIR / f"{table}.csv").open().readline().strip().split(",")
        if header != [c.split()[0] for c in columns.split(", ")]:
            sys.exit(f"{table}.csv header {header} does not match the schema")
        con.execute(f"create table {table} ({columns})")
        con.execute(f"copy {table} from '{CSV_DIR / (table + '.csv')}' (header, nullstr '')")
    counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in SCHEMA}
    con.close()
    tmp.replace(out)
    return counts


def read_doc(path):
    lines = path.read_text().split("\n")
    head = dict(line.split(": ", 1) for line in lines[:4])
    return head["DOC-ID"], head["Title"], "\n".join(lines[5:]).strip()


def chunk(body, title, size):
    """[(headings, text)]: `##` sections merged up to size characters. The `# Title` intro is a section too."""
    sections, current = [], []
    for line in body.split("\n"):
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = []
        current.append(line)
    sections.append("\n".join(current).strip())
    chunks, text, heads = [], "", []
    for section in sections:
        head = section.split("\n", 1)[0].lstrip("# ").strip() if section.startswith("#") else title
        if text and len(text) + 2 + len(section) > size:
            chunks.append((heads, text))
            text, heads = "", []
        text, heads = (text + "\n\n" + section if text else section), heads + [head]
    chunks.append((heads, text))
    return chunks


def corpus_chunks(size):
    rows = []
    for path in sorted(p for p in CORPUS.glob("*.md") if p.name != "README.md"):
        doc_id, title, body = read_doc(path)
        for n, (heads, text) in enumerate(chunk(body, title, size), 1):
            embed_text = f"{title}\n{' / '.join(heads)}\n\n{re.sub(r'^# .*\n+', '', text)}"
            rows.append({"chunk_id": f"{doc_id}#{n}", "doc_id": doc_id, "chunk_no": n, "title": title,
                         "headings": " / ".join(heads), "text": text, "embed_text": embed_text})
    return rows


def build_docs(out=tools.DOCS_DB):
    cfg = tools.settings()
    rows = corpus_chunks(cfg["chunk_chars"])
    vectors = tools.embed([r["embed_text"] for r in rows], cfg["embed_model"])
    dims = len(vectors[0])
    tmp = fresh(out)
    con = duckdb.connect(str(tmp))
    con.execute(f"""create table chunks (chunk_id VARCHAR primary key, doc_id VARCHAR, chunk_no INTEGER,
                    title VARCHAR, headings VARCHAR, text VARCHAR, embed_text VARCHAR, embedding FLOAT[{dims}])""")
    con.executemany("insert into chunks values (?, ?, ?, ?, ?, ?, ?, ?)",
                    [[*r.values(), v] for r, v in zip(rows, vectors)])
    con.execute("create table index_settings (key VARCHAR, value VARCHAR)")
    con.executemany("insert into index_settings values (?, ?)", [
        ["embed_model", cfg["embed_model"]], ["chunk_chars", str(cfg["chunk_chars"])], ["dims", str(dims)],
        ["chunks", str(len(rows))], ["built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")]])
    con.close()
    tmp.replace(out)
    return len(rows), dims


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=["db", "docs"])
    if parser.parse_args().what == "db":
        for table, n in build_db().items():
            print(f"{table}: {n:,} rows")
        print(f"wrote {tools.TABLES_DB.relative_to(tools.ROOT)}")
    else:
        n, dims = build_docs()
        print(f"wrote {tools.DOCS_DB.relative_to(tools.ROOT)}: {n} chunks, {dims}-dim embeddings")
