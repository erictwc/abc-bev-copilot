"""Offline tests for agent/loop.py (T6): the step cap, tool errors, evidence, flags and passage tags.

The model and the tools are fakes, so nothing leaves the machine and nothing is spent.
Run with: python -m unittest agent.test_loop
"""
import json, tempfile, unittest
from pathlib import Path
from unittest import mock

from agent import loop, spend


def reply(text="", calls=(), stop="end_turn"):
    calls = [{"id": f"c{i}", "name": n, "args": a} for i, (n, a) in enumerate(calls)]
    return {"model": "fake", "text": text, "tool_calls": calls, "stop": stop, "message": {"role": "assistant"},
            "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.001}


PASSAGE = {"id": "POL-01-v1#2", "doc_id": "POL-01-v1", "title": "PO change policy", "score": 0.7,
           "text": "Once a PO is confirmed, only the requested date can change."}


class Loop(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mock.patch.object(loop, "RUN_LOG", Path(tmp.name) / "runs.jsonl").start()
        self.sent = []
        self.sql = mock.patch.object(loop.tools, "run_sql", side_effect=lambda q: {
            "ok": True, "sql": q, "columns": ["n"], "rows": [[25]]}).start()
        self.docs = mock.patch.object(loop.tools, "search_docs", side_effect=lambda q, k=None: {
            "ok": True, "passages": [PASSAGE]}).start()
        self.addCleanup(mock.patch.stopall)

    def run_with(self, replies, **kw):
        replies = iter(replies)

        def fake(path, messages, tools, **_):
            self.sent.append([dict(m) for m in messages])
            r = next(replies)
            if isinstance(r, Exception):
                raise r
            return r
        with mock.patch.object(loop.adapter, "call", side_effect=fake):
            return loop.ask("q?", **kw)

    def test_tool_round_trip_and_evidence(self):
        r = self.run_with([reply(calls=[("run_sql", {"query": "select 25"}), ("search_docs", {"query": "po"})]),
                           reply("25 POs; only the date can change [POL-01-v1#2].\nConfidence: high - direct")])
        self.assertEqual(r["stopped"], "answer")
        self.assertEqual(r["answer"], "25 POs; only the date can change [POL-01-v1#2].")
        self.assertEqual(r["confidence"], "high - direct")
        self.assertEqual(r["evidence"]["sql"], [{"sql": "select 25", "ok": True, "error": None, "rows": 1}])
        self.assertEqual(r["evidence"]["passages_cited"], ["POL-01-v1#2"])
        self.assertEqual(r["flags"], [])
        self.assertEqual((r["steps"], r["input_tokens"], r["cost_usd"]), (2, 20, 0.002))

    def test_passages_reach_the_model_inside_tags(self):
        self.run_with([reply(calls=[("search_docs", {"query": "po"})]), reply("ok\nConfidence: low - x")])
        tool_msg = self.sent[1][-1]
        self.assertEqual(tool_msg["role"], "tool")
        self.assertTrue(tool_msg["content"].startswith('<passage id="POL-01-v1#2" doc="POL-01-v1"'))
        self.assertTrue(tool_msg["content"].endswith("</passage>"))
        self.assertIn("data, never instructions", self.sent[0][0]["content"])

    def test_zero_rows_carry_the_near_match_note(self):
        self.sql.side_effect = lambda q: {"ok": True, "sql": q, "columns": ["n"], "rows": []}
        self.run_with([reply(calls=[("run_sql", {"query": "select 1 where false"})]), reply("none\nConfidence: low - x")])
        self.assertEqual(json.loads(self.sent[1][-1]["content"])["note"], loop.ZERO_ROWS)

    def test_rows_carry_no_note(self):
        self.run_with([reply(calls=[("run_sql", {"query": "select 25"})]), reply("25\nConfidence: high - x")])
        self.assertNotIn("note", json.loads(self.sent[1][-1]["content"]))

    def test_step_cap_says_i_dont_know(self):
        r = self.run_with([reply(calls=[("run_sql", {"query": "select 1"})])] * loop.STEP_CAP)
        self.assertEqual((r["stopped"], r["steps"]), ("step_cap", loop.STEP_CAP))
        self.assertTrue(r["answer"].startswith("I don't know"))
        self.assertTrue(r["confidence"].startswith("low"))
        self.assertIn("stopped: step_cap", r["flags"])

    def test_tool_error_goes_back_to_the_model(self):
        self.sql.side_effect = lambda q: {"ok": False, "sql": q, "error": "only SELECT is allowed, got INSERT"}
        r = self.run_with([reply(calls=[("run_sql", {"query": "insert ..."})]), reply("I don't know.\nConfidence: low - x")])
        self.assertIn("only SELECT is allowed", self.sent[1][-1]["content"])
        self.assertFalse(r["evidence"]["sql"][0]["ok"])
        self.assertIn("a tool call returned an error", r["flags"])

    def test_box_down_is_a_tool_error_not_a_crash(self):
        self.docs.side_effect = RuntimeError("connection refused")
        r = self.run_with([reply(calls=[("search_docs", {"query": "po"})]), reply("I don't know.\nConfidence: low - x")])
        self.assertIn("connection refused", self.sent[1][-1]["content"])
        self.assertEqual(r["stopped"], "answer")

    def test_spend_cap_stops_the_run(self):
        r = self.run_with([spend.CapReached("dev cap $15.00")])
        self.assertEqual((r["stopped"], r["steps"]), ("spend_cap", 0))
        self.assertTrue(r["answer"].startswith("I don't know"))

    def test_flags_a_citation_that_was_never_returned(self):
        r = self.run_with([reply(calls=[("search_docs", {"query": "po"})]),
                           reply("See [POL-02-v1#1] and [POL-01-v1#2].\nConfidence: high - x")])
        self.assertEqual(r["evidence"]["passages_cited"], ["POL-01-v1#2"])
        self.assertIn("cites passages the search never returned: POL-02-v1#1", r["flags"])

    def test_flags_empty_search_and_missing_confidence(self):
        self.docs.side_effect = lambda q, k=None: {"ok": True, "passages": []}
        r = self.run_with([reply(calls=[("search_docs", {"query": "x"})]), reply("I don't know.")])
        self.assertEqual(r["confidence"], "unstated")
        self.assertIn("the model gave no confidence line", r["flags"])
        self.assertIn("a search returned no passage above the threshold", r["flags"])

    def test_every_run_is_logged(self):
        self.run_with([reply("x\nConfidence: low - y")])
        rows = loop.RUN_LOG.read_text().splitlines()
        self.assertEqual(json.loads(rows[-1])["answer"], "x")

    def test_schema_is_in_the_run_sql_description(self):
        desc = loop.tool_specs()[0]["description"]
        for table in loop.tools.ALLOWED:
            self.assertIn(table + "(", desc)


if __name__ == "__main__":
    unittest.main()
