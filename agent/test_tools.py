"""Offline tests for agent/tools.py and agent/index.py (T5): run_sql's guard rails, chunking, and search_docs.

The tables are built from data/csv/ into a temporary DuckDB file. Embeddings are replaced by a fake,
so no request leaves the machine. Live retrieval against the box is agent/test_retrieval.py.
Run with: python -m unittest agent.test_tools
"""
import csv, tempfile, time, unittest
from pathlib import Path
from unittest import mock

import duckdb

from agent import index, tools


class Isolated(unittest.TestCase):
    """A temporary tables file and tool log, so no test touches the real ones."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "abc.duckdb"
        index.build_db(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.log = Path(self.tmp.name) / "tools.csv"
        self.log.unlink(missing_ok=True)
        patch = mock.patch.object(tools, "TOOL_LOG", self.log)
        patch.start()
        self.addCleanup(patch.stop)

    def sql(self, query):
        return tools.run_sql(query, db=self.db)

    def refused(self, query, reason):
        out = self.sql(query)
        self.assertFalse(out["ok"], f"should be refused: {query}")
        self.assertIn(reason, out["error"])
        self.assertNotIn("rows", out)
        return out


class RunSqlRefuses(Isolated):
    def test_insert_and_other_writes(self):
        for q in ["insert into sku_master values ('X', 'X', 'X', 'X', 1, 'X', 'X')",
                  "update sku_master set status = 'active'", "delete from promo_calendar",
                  "drop table sku_master", "create table t (x int)", "copy sku_master to 'out.csv'",
                  "attach 'other.duckdb'", "set enable_external_access = true", "pragma show_tables"]:
            self.refused(q, "only SELECT is allowed")

    def test_writes_fail_even_past_the_statement_check(self):
        """Layer 1 on its own: the connection cannot write, read files or unlock its settings."""
        con = tools.connect(self.db)
        for q in ["insert into sku_master select * from sku_master", "select * from read_csv('data/csv/sku_master.csv')",
                  "set enable_external_access = true"]:
            with self.assertRaises(duckdb.Error):
                con.execute(q)
        con.close()

    def test_multiple_statements(self):
        for q in ["select 1; select 2", "select * from sku_master; drop table sku_master",
                  "select 1; insert into sku_master select * from sku_master"]:
            self.refused(q, "exactly one statement")

    def test_tables_outside_the_allow_list(self):
        for q, reason in [
                ("select * from information_schema.tables", "not allowed"),
                ("select * from duckdb_tables", "not allowed"),
                ("select * from duckdb_tables()", "table function"),
                ("select * from duckdb_settings()", "table function"),
                ("select * from read_csv('data/csv/sku_master.csv')", "table function"),
                ("select * from 'data/csv/sku_master.csv'", "not allowed"),
                ("select * from sku_master, unnest([1, 2])", "table function"),
                ("select * from no_such_table", "not allowed"),
                ("select * from system.main.duckdb_views", "not allowed"),
                ("select * from abc.main.sku_master", "not allowed"),
                ("select (select count(*) from duckdb_views) from sku_master", "not allowed"),
                ("select * from sku_master where sku_id in (select table_name from information_schema.tables)",
                 "not allowed"),
                ("describe sku_master", "show ref"),
                ("show all tables", "show ref"),
                ("summarize sku_master", "show ref")]:
            with self.subTest(q):
                self.refused(q, reason)

    def test_a_cte_cannot_shadow_a_system_table(self):
        """Out of the CTE's scope the same name would bind to the system view."""
        self.refused("select * from (with duckdb_tables as (select 1) select * from duckdb_tables) x, duckdb_tables",
                     "may not be named")

    def test_oversized_result(self):
        out = self.refused("select * from distributor_orders", f"more than {tools.ROW_LIMIT} rows")
        self.assertEqual(out["sql"], "select * from distributor_orders")

    def test_long_running_query(self):
        heavy = ("select count(*) from distributor_depletions a, distributor_depletions b, distributor_depletions c "
                 "where hash(a.sku_id, b.week_ending, c.distributor) = 0")  # statistics cannot rule this out
        with mock.patch.object(tools, "TIMEOUT_S", 0.5):
            start = time.monotonic()
            self.refused(heavy, "timeout")
            self.assertLess(time.monotonic() - start, 3)

    def test_errors_are_returned_not_raised(self):
        self.refused("select no_such_column from sku_master", "BinderException")
        self.refused("selec 1", "could not parse")


class RunSqlAnswers(Isolated):
    def test_counts_match_the_csvs(self):
        for table in tools.ALLOWED:
            with open(index.CSV_DIR / f"{table}.csv") as f:
                expected = sum(1 for _ in f) - 1
            self.assertEqual(self.sql(f"select count(*) from {table}")["rows"], [[expected]])

    def test_explicit_types_and_nulls(self):
        out = self.sql("select * from promo_calendar where authorized is null")      # DP-05 stays NULL
        self.assertEqual(len(out["rows"]), 1)
        self.assertEqual(out["rows"][0][3], "2026-11-09")                           # DATE comes back as ISO text
        con = duckdb.connect(str(self.db), read_only=True)
        types = dict(con.execute("select column_name, data_type from information_schema.columns "
                                 "where table_name = 'distributor_orders'").fetchall())
        con.close()
        self.assertEqual((types["qty"], types["order_date"], types["carrier"]), ("INTEGER", "DATE", "VARCHAR"))

    def test_exactly_the_row_limit_is_allowed(self):
        out = self.sql(f"select po_id from distributor_orders order by po_id limit {tools.ROW_LIMIT}")
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["rows"]), tools.ROW_LIMIT)

    def test_ctes_joins_and_aggregates(self):
        out = self.sql("with shipped as (select * from distributor_orders where status = 'shipped') "
                       "select s.brand, count(*) from shipped o join sku_master s using (sku_id) group by 1 order by 1")
        self.assertTrue(out["ok"])
        self.assertEqual(out["columns"], ["brand", "count_star()"])

    def test_every_call_is_logged(self):
        self.sql("select 1")
        self.sql("select 1; select 2")
        rows = list(csv.DictReader(self.log.open()))
        self.assertEqual([r["ok"] for r in rows], ["True", "False"])
        self.assertIn('"row_limit": 200', rows[0]["settings"])


class Chunking(unittest.TestCase):
    def test_every_document_is_chunked_and_numbered_from_one(self):
        rows = index.corpus_chunks(800)
        docs = {r["doc_id"] for r in rows}
        self.assertEqual(len(docs), 28)
        for doc in docs:
            numbers = [r["chunk_no"] for r in rows if r["doc_id"] == doc]
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertTrue(all(r["chunk_id"] == f"{r['doc_id']}#{r['chunk_no']}" for r in rows))

    def test_sections_are_merged_up_to_the_size_and_never_split(self):
        body = "# T\n\nIntro.\n\n## A\n\n" + "a" * 300 + "\n\n## B\n\n" + "b" * 300 + "\n\n## C\n\n" + "c" * 900
        chunks = index.chunk(body, "T", 800)
        self.assertEqual([heads for heads, _ in chunks], [["T", "A", "B"], ["C"]])
        self.assertIn("c" * 900, chunks[1][1])          # a section longer than the size stays whole

    def test_embedded_text_names_the_document_and_section(self):
        row = next(r for r in index.corpus_chunks(800) if r["chunk_id"] == "POL-01-v1#2")
        self.assertTrue(row["embed_text"].startswith("PO change policy\nCut-off"))
        self.assertNotIn("DOC-ID:", row["text"])


def fake_embed(texts, model):
    """Two-dimensional stand-in: kiwi points one way, everything else the other."""
    return [[1.0, 0.0] if "kiwi" in t.lower() else [0.0, 1.0] for t in texts]


class SearchDocs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "docs.duckdb"
        patches = [mock.patch.object(tools, "embed", fake_embed),
                   mock.patch.object(tools, "TOOL_LOG", Path(self.tmp.name) / "tools.csv")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        index.build_docs(self.db)

    def test_top_k_above_the_threshold_with_citations(self):
        out = tools.search_docs("frost kiwi caffeine", k=3, db=self.db)
        self.assertTrue(out["ok"])
        self.assertEqual([p["doc_id"] for p in out["passages"]], ["PRD-TRV-KIW-v1"])  # the rest score 0
        self.assertEqual(out["passages"][0]["id"], "PRD-TRV-KIW-v1#1")
        self.assertEqual(out["settings"]["k"], 3)

    def test_k_is_capped(self):
        out = tools.search_docs("anything", k=1000, db=self.db)
        self.assertEqual(out["settings"]["k"], tools.MAX_K)
        self.assertEqual(len(out["passages"]), tools.MAX_K)

    def test_an_index_built_with_other_settings_is_refused(self):
        cfg = {**tools.settings(), "chunk_chars": 500}
        with mock.patch.object(tools, "settings", return_value=cfg):
            out = tools.search_docs("anything", db=self.db)
        self.assertFalse(out["ok"])
        self.assertIn("make index", out["error"])

    def test_settings_are_logged(self):
        tools.search_docs("kiwi", db=self.db)
        row = next(csv.DictReader((Path(self.tmp.name) / "tools.csv").open()))
        self.assertEqual(row["tool"], "search_docs")
        for key in ("embed_model", "chunk_chars", "threshold", '"k"'):
            self.assertIn(key, row["settings"])


if __name__ == "__main__":
    unittest.main()
