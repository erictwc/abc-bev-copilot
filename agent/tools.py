"""The agent's two tools (T5): run_sql over the six v1 tables and search_docs over the corpus.

run_sql is read-only and layered, so no single check has to be perfect (D47, D52, D53, D55):
  1. the connection is opened read-only, with file access off and its configuration locked
  2. the text must be exactly one statement, and it must be a SELECT
  3. every table in DuckDB's parse of the query must be one of ALLOWED (or a CTE it defines),
     and no table function may appear; get_table_names() alone misses information_schema
  4. more than ROW_LIMIT rows is refused, not truncated
  5. a query still running after TIMEOUT_S is interrupted
The limits are constants here, not config, so changing one is a reviewed commit (D54).

search_docs embeds the question on the GEEKOM box (D49) and returns the top-k chunks above the
score threshold from data/docs.duckdb (D48, D51). Passage text is data, never instructions.
Both tools return plain dicts and append one row per call to logs/tools.csv (D54).
"""
import csv, ipaddress, json, socket, threading, time, tomllib, urllib.parse
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

from agent import adapter

ROOT = Path(__file__).resolve().parent.parent
TABLES_DB = ROOT / "data" / "abc.duckdb"      # built by `make db` (D55)
DOCS_DB = ROOT / "data" / "docs.duckdb"       # built by `make index` (D48)
CONFIG = ROOT / "config.toml"
TOOL_LOG = ROOT / "logs" / "tools.csv"

ALLOWED = ("sku_master", "distributor_orders", "copacker_plan",
           "warehouse_inventory", "promo_calendar", "distributor_depletions")
ROW_LIMIT = 200        # D52
TIMEOUT_S = 10         # D53
MAX_K = 10             # a model asking for k=1000 gets at most this many passages

LOG_FIELDS = ["timestamp", "tool", "input", "settings", "ok", "result", "latency_s"]


def settings():
    return tomllib.loads(CONFIG.read_text())["retrieval"]


def log(tool, given, used, out, start):
    TOOL_LOG.parent.mkdir(exist_ok=True)
    new = not TOOL_LOG.exists()
    result = out.get("error") or (f"{len(out['rows'])} rows" if "rows" in out
                                  else " ".join(f"{p['id']}:{p['score']}" for p in out["passages"]))
    with TOOL_LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": tool,
                    "input": json.dumps(given), "settings": json.dumps(used), "ok": out["ok"],
                    "result": result, "latency_s": round(time.monotonic() - start, 3)})
    return out


# ---- run_sql ---------------------------------------------------------------------------------

def connect(path=None):
    return duckdb.connect(str(path or TABLES_DB), read_only=True,
                          config={"enable_external_access": False, "lock_configuration": True})


def plain(value):
    """JSON-friendly cell values: dates as ISO text, decimals as floats."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return float(value) if isinstance(value, Decimal) else value


def nodes(tree):
    if isinstance(tree, dict):
        yield tree
        tree = list(tree.values())
    if isinstance(tree, list):
        for item in tree:
            yield from nodes(item)


# Every FROM item in DuckDB's parse tree carries a "sample" key. Only these kinds may appear: a table
# function (read_csv, duckdb_tables(), unnest in FROM ...) or a SHOW/DESCRIBE/SUMMARIZE is refused.
FROM_KINDS = {"SELECT_NODE", "SET_OPERATION_NODE", "RECURSIVE_CTE_NODE", "CTE_NODE",
              "BASE_TABLE", "SUBQUERY", "JOIN", "EXPRESSION_LIST", "EMPTY", "PIVOT"}


def check_tables(con, query):
    """None if every table the query reads is allow-listed, else the reason it is refused."""
    parsed = json.loads(con.execute("select json_serialize_sql(?)", [query]).fetchone()[0])
    if parsed.get("error"):
        return f"could not parse the query: {parsed.get('error_message', '')}"
    # A CTE may not reuse the name of a system table or view: one defined inside a subquery is out of
    # scope outside it, where the same name would quietly bind to that system object instead.
    existing = {r[0].lower() for r in con.execute(
        "select view_name from duckdb_views() union select table_name from duckdb_tables()").fetchall()}
    ctes = {entry["key"].lower() for n in nodes(parsed) if "cte_map" in n for entry in n["cte_map"]["map"]}
    if clash := sorted((ctes & existing) - set(ALLOWED)):
        return f"a CTE may not be named {clash[0]!r}, the name of a system table"
    for n in nodes(parsed):
        if "sample" in n and n.get("type") not in FROM_KINDS:
            return (f"{n.get('type', '?').lower().replace('_', ' ')} is not allowed in FROM; "
                    f"query the tables by name: {', '.join(ALLOWED)}")
        if n.get("type") == "BASE_TABLE":
            name, schema, catalog = n["table_name"].lower(), n.get("schema_name", ""), n.get("catalog_name", "")
            if catalog or schema not in ("", "main"):
                return f"table {'.'.join(x for x in (catalog, schema, name) if x)} is not allowed"
            if name not in ALLOWED and name not in ctes:
                return f"table {name!r} is not allowed; allowed tables: {', '.join(ALLOWED)}"
    return None


def run_sql(query, db=None):
    """Run one read-only SELECT. Returns {ok, sql, columns, rows} or {ok: False, sql, error}."""
    start, used = time.monotonic(), {"row_limit": ROW_LIMIT, "timeout_s": TIMEOUT_S}
    out = {"ok": False, "sql": query}
    try:
        statements = duckdb.extract_statements(query)
    except duckdb.Error as e:
        return log("run_sql", query, used, {**out, "error": f"could not parse the query: {e}"}, start)
    if len(statements) != 1:
        return log("run_sql", query, used, {**out, "error": f"exactly one statement is allowed, got {len(statements)}"}, start)
    if statements[0].type != duckdb.StatementType.SELECT:
        return log("run_sql", query, used, {**out, "error": f"only SELECT is allowed, got {statements[0].type.name}"}, start)
    con = connect(db)
    try:
        if reason := check_tables(con, query):
            return log("run_sql", query, used, {**out, "error": reason}, start)
        timer = threading.Timer(TIMEOUT_S, con.interrupt)
        timer.start()
        try:
            cur = con.execute(query)
            rows = cur.fetchmany(ROW_LIMIT + 1)
        except duckdb.InterruptException:
            return log("run_sql", query, used, {**out, "error": f"query stopped after the {TIMEOUT_S} s timeout"}, start)
        except duckdb.Error as e:
            return log("run_sql", query, used, {**out, "error": f"{type(e).__name__}: {e}"}, start)
        finally:
            timer.cancel()
        if len(rows) > ROW_LIMIT:
            return log("run_sql", query, used, {**out, "error": f"more than {ROW_LIMIT} rows; add a filter, "
                                                "an aggregate or a LIMIT"}, start)
        out = {"ok": True, "sql": query, "columns": [d[0] for d in cur.description],
               "rows": [[plain(v) for v in row] for row in rows]}
        return log("run_sql", query, used, out, start)
    finally:
        con.close()


# ---- search_docs -----------------------------------------------------------------------------

def box():
    """The Ollama base URL, refused unless it resolves to a home-network address (D11), as in the adapter."""
    host = adapter.key("OLLAMA_HOST")
    url = urllib.parse.urlsplit(host if "://" in host else "http://" + host)
    for info in socket.getaddrinfo(url.hostname, None):
        if not (ip := ipaddress.ip_address(info[4][0].split("%")[0])).is_private and not ip.is_loopback:
            raise RuntimeError(f"refusing {url.hostname}: {ip} is not a home-network address")
    return f"http://{url.hostname}:{url.port or 11434}"


def embed(texts, model):
    r = adapter.post(f"{box()}/api/embed", {"model": model, "input": list(texts)}, {}, 600)
    return r["embeddings"]


def search_docs(query, k=None, db=None):
    """Top-k passages scoring at least the threshold: {ok, passages: [{id, doc_id, title, score, text}], settings}."""
    start, cfg = time.monotonic(), settings()
    k = max(1, min(int(k or cfg["k"]), MAX_K))
    used = {"embed_model": cfg["embed_model"], "chunk_chars": cfg["chunk_chars"], "k": k, "threshold": cfg["threshold"]}
    given = {"query": query, "k": k}
    con = duckdb.connect(str(db or DOCS_DB), read_only=True,
                         config={"enable_external_access": False, "lock_configuration": True})
    try:
        built = dict(con.execute("select key, value from index_settings").fetchall())
        for name in ("embed_model", "chunk_chars"):
            if built.get(name) != str(cfg[name]):
                out = {"ok": False, "error": f"the index was built with {name}={built.get(name)}, config says "
                       f"{cfg[name]}; run make index", "passages": []}
                return log("search_docs", given, used, out, start)
        vector = embed([cfg["query_prefix"] + query], cfg["embed_model"])[0]
        dims = int(built["dims"])
        rows = con.execute(f"""
            select chunk_id, doc_id, title, text, array_cosine_similarity(embedding, ?::float[{dims}]) as score
            from chunks where score >= ? order by score desc, chunk_id limit ?""",
                           [vector, cfg["threshold"], k]).fetchall()
    finally:
        con.close()
    passages = [{"id": cid, "doc_id": doc, "title": title, "score": round(score, 4), "text": text}
                for cid, doc, title, text, score in rows]
    return log("search_docs", given, used, {"ok": True, "passages": passages, "settings": used}, start)
