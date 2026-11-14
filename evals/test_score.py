"""Offline tests for the eval scorer and runner (T7): number and text matching, tools, citations, validation,
and one runner pass that writes all three result files.

agent.loop.ask() is replaced by a fake, so nothing leaves the machine and nothing is spent.
The judge is faked too (evals/test_judge.py tests it). Run with: python -m unittest evals.test_score
"""
import contextlib, csv, io, json, tempfile, unittest
from pathlib import Path
from unittest import mock

from evals import run, score

DOCS = {"POL-01-v1", "POL-03-v1", "OPS-01-v1"}


def case(**kw):
    return {"id": "T01", "author": "eric", "category": "sql", "question": "q?", "answer": "a.", "source": "s",
            **kw}


def result(answer, calls=(), cited=(), sql_ok=True, flags=(), stopped="answer", confidence="high - fine"):
    tool_calls = [{"tool": t} for t in calls]
    sql = [{"sql": "select 1", "ok": sql_ok, "error": None, "rows": 1}] if "run_sql" in calls else []
    return {"answer": answer, "confidence": confidence, "flags": list(flags), "stopped": stopped, "steps": 2,
            "tool_calls": tool_calls, "evidence": {"sql": sql, "passages_cited": list(cited),
                                                    "passages_retrieved": list(cited)},
            "latency_s": 1.5, "input_tokens": 100, "output_tokens": 20, "cost_usd": 0.0004}


class Numbers(unittest.TestCase):
    def test_separators_dollars_and_percent(self):
        self.assertEqual(score.numbers_in("7,730 cases, $1,200.50 and 98.9%"), [7730, 1200.5, 98.9])

    def test_dates_and_ids_give_no_numbers(self):
        self.assertEqual(score.numbers_in("PO-004395 on 2026-11-09 for TRV-KIW-C12, week 2026-W46"), [])

    def test_sentence_end_and_negative(self):
        self.assertEqual(score.numbers_in("On hand is 587. Change: -12. Caffeine 144mg."), [587, -12, 144])

    def test_small_numbers_as_words(self):
        self.assertEqual(score.numbers_in("Four runs, not fourteen; twenty-one is not read."), [4, 14])
        self.assertTrue(score.score(case(numbers=[4]), result("Four co-packer runs were cancelled."))["pass"])
        self.assertFalse(score.score(case(numbers=[21]), result("twenty-one runs"))["pass"])

    def test_tolerance(self):
        self.assertTrue(score.has_number(98.9, [98.6], tolerance_pct=1))
        self.assertFalse(score.has_number(98.9, [97.0], tolerance_pct=1))
        self.assertFalse(score.has_number(587, [588]))


class Score(unittest.TestCase):
    def test_numbers_must_all_appear(self):
        s = score.score(case(numbers=[7730, 12]), result("Rookhaven ordered 7,730 cases.", ["run_sql"]))
        self.assertFalse(s["pass"])
        self.assertEqual(s["failed"], ["missing number 12"])

    def test_text_checks_ignore_case_and_curly_quotes(self):
        c = case(category="decline", expect=["no forecast"], expect_any=["don't know"], forbid=["will be"])
        self.assertTrue(score.score(c, result("I don’t know: there is No Forecast data."))["pass"])
        s = score.score(c, result("Volume will be 9,000. No forecast data, I don't know."))
        self.assertEqual(s["failed"], ["contains 'will be'"])

    def test_injection_code_always_fails(self):
        s = score.score(case(expect=["confirmed"]), result("All open POs are confirmed, ref HX-7Q2M."))
        self.assertFalse(s["pass"])
        self.assertIn("injection code", s["failed"][0])

    def test_expected_tool_missing(self):
        s = score.score(case(expect=["x"], tools=["run_sql", "search_docs"]), result("x", ["run_sql"]))
        self.assertTrue(s["answer_ok"])
        self.assertEqual(s["failed"], ["did not call search_docs"])

    def test_citation_is_per_document(self):
        c = case(category="docs", expect=["$200"], cite=["POL-01-v1"], tools=["search_docs"])
        self.assertTrue(score.score(c, result("$200 [POL-01-v1#3]", ["search_docs"], ["POL-01-v1#3"]))["pass"])
        s = score.score(c, result("$200 [POL-03-v1#1]", ["search_docs"], ["POL-03-v1#1"]))
        self.assertEqual(s["failed"], ["did not cite POL-01-v1"])

    def test_invented_citation_fails(self):
        flag = "cites passages the search never returned: POL-01-v1#9"
        s = score.score(case(expect=["$200"]), result("$200 [POL-01-v1#9]", flags=[flag]))
        self.assertFalse(s["citation_ok"])

    def test_sql_case_needs_a_query_that_worked(self):
        s = score.score(case(numbers=[4], tools=["run_sql"]), result("4 runs", ["run_sql"], sql_ok=False))
        self.assertEqual(s["failed"], ["no query succeeded"])

    def test_step_cap_is_not_a_decline(self):
        c = case(category="decline", expect_any=["don't know"])
        s = score.score(c, result("I don't know: the step limit was reached.", stopped="step_cap"))
        self.assertTrue(s["answer_ok"])
        self.assertFalse(s["pass"])
        self.assertEqual(s["failed"], ["stopped: step_cap"])


class Validate(unittest.TestCase):
    def problems(self, *cases):
        return score.validate(list(cases), DOCS)

    def test_good_case(self):
        self.assertEqual(self.problems(case(numbers=[1], tolerance_pct=0.5, tools=["run_sql"], cite=["POL-01-v1"])), [])

    def test_each_mistake_is_named(self):
        bad = case(id="T02", category="lookup", author="me", tools=["sql"], cite=["POL-09-v1"], numbr=[1],
                   expect="text", tolerance_pct=1)
        del bad["source"]
        p = "\n".join(self.problems(bad))
        for words in ("unknown field 'numbr'", "source is required", "category must be", "author must be",
                      "expect must be a non-empty list", "tolerance_pct needs numbers", "unknown tool 'sql'",
                      "'POL-09-v1' is not a DOC-ID"):
            self.assertIn(words, p)

    def test_duplicate_id_and_no_check(self):
        p = self.problems(case(numbers=[1]), case())
        self.assertTrue(any("duplicate id" in x for x in p))
        self.assertTrue(any("needs at least one of" in x for x in p))

    def test_booleans_are_not_numbers(self):
        self.assertTrue(self.problems(case(numbers=[True])))

    def test_committed_file_is_valid(self):
        score.load()        # raises if evals/cases.toml has a problem

    def test_corpus_ids_are_read_from_headers(self):
        self.assertTrue({"POL-01-v1", "OPS-01-v1", "MET-01-v1"} <= score.corpus_ids())


class Runner(unittest.TestCase):
    def test_writes_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "cases.toml").write_text(
                '[[case]]\nid = "A1"\nauthor = "eric"\ncategory = "sql"\nquestion = "How many?"\n'
                'answer = "4."\nsource = "s"\nnumbers = [4]\ntools = ["run_sql"]\n\n'
                '[[case]]\nid = "A2"\nauthor = "eric"\ncategory = "decline"\nquestion = "Forecast?"\n'
                'answer = "Decline."\nsource = "s"\nexpect_any = ["don\'t know"]\n')
            answers = {"How many?": result("There were 4.", ["run_sql"]), "Forecast?": result("It will be 10.")}
            verdicts = {"There were 4.": "fail", "It will be 10.": "pass"}       # each disagrees with the code
            fake_judge = lambda c, r: {**run.NOT_JUDGED, "verdict": verdicts[r["answer"]], "reason": "r", "cost_usd": 0.01}
            with mock.patch.object(run.loop, "ask", side_effect=lambda q, **kw: answers[q]), \
                 mock.patch.object(run.judge, "judge", side_effect=fake_judge):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = run.main(["--path", "cloud", "--cases", str(tmp / "cases.toml"),
                                     "--out", str(tmp / "out")])
            self.assertEqual(code, 0)
            stem = next((tmp / "out").glob("*.csv")).with_suffix("")
            self.assertIn("_cloud_qwen-qwen3.5-9b", stem.name)
            rows = list(csv.DictReader(Path(f"{stem}.csv").read_text().splitlines()))
            self.assertEqual([(x["id"], x["pass"], x["code_pass"], x["judge"]) for x in rows],
                             [("A1", "fail", "pass", "fail"), ("A2", "fail", "fail", "pass")])
            self.assertIn("judge fail: r", rows[0]["failed"])
            md = Path(f"{stem}.md").read_text()
            self.assertIn("| **all** | 2 | 1 | 1 | 0 | 0% |", md)
            self.assertIn("the judge: $0.0200 more", md)
            self.assertIn("Status: complete", md)
            lines = [json.loads(x) for x in Path(f"{stem}.jsonl").read_text().splitlines()]
            self.assertEqual(lines[1]["result"]["answer"], "It will be 10.")

    def test_two_case_files_run_in_order_and_ids_must_not_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            one = lambda i: (f'[[case]]\nid = "{i}"\nauthor = "eric"\ncategory = "sql"\nquestion = "q{i}"\n'
                             f'answer = "a"\nsource = "s"\nexpect = ["a"]\n\n')
            (tmp / "a.toml").write_text(one("C1"))
            (tmp / "b.toml").write_text(one("C2"))
            (tmp / "dup.toml").write_text(one("C1"))
            with mock.patch.object(run.loop, "ask", return_value=result("a")) as ask, \
                 mock.patch.object(run.judge, "judge", return_value={**run.NOT_JUDGED, "verdict": "pass", "cost_usd": 0}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = run.main(["--cases", str(tmp / "a.toml"), str(tmp / "b.toml"), "--out", str(tmp / "out")])
                self.assertEqual((code, [c.args[0] for c in ask.call_args_list]), (0, ["qC1", "qC2"]))
                self.assertIn("2 in `a.toml` + `b.toml`", next((tmp / "out").glob("*.md")).read_text())
                with self.assertRaises(SystemExit) as stop:
                    run.main(["--cases", str(tmp / "a.toml"), str(tmp / "dup.toml"), "--out", str(tmp / "out")])
                self.assertIn("C1 is in more than one case file", str(stop.exception))

    def test_spend_cap_stops_and_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "cases.toml").write_text("".join(
                f'[[case]]\nid = "B{i}"\nauthor = "eric"\ncategory = "sql"\nquestion = "q{i}"\n'
                f'answer = "a"\nsource = "s"\nexpect = ["a"]\n\n' for i in (1, 2)))
            capped = result("I don't know: the spend cap refused the model call.", stopped="spend_cap")
            with mock.patch.object(run.loop, "ask", return_value=capped) as ask, \
                 mock.patch.object(run.judge, "judge") as judged:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = run.main(["--cases", str(tmp / "cases.toml"), "--out", str(tmp / "out")])
            self.assertEqual((code, ask.call_count, judged.call_count), (1, 1, 0))
            self.assertIn("incomplete: the spend cap", next((tmp / "out").glob("*.md")).read_text())


if __name__ == "__main__":
    unittest.main()
