"""Offline tests for agent/adapter.py and agent/spend.py (T4): the spend cap, the spend log, retries and message conversion.

No request leaves the machine: HTTP is replaced by fakes, and the spend log is a temporary file.
Run with: python -m unittest agent.test_adapter
"""
import csv, io, json, tempfile, unittest, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from agent import adapter, spend

HELLO = [{"role": "user", "content": "Say OK."}]
CLAUDE_OK = {"content": [{"type": "text", "text": "OK"}], "usage": {"input_tokens": 1000, "output_tokens": 100},
             "stop_reason": "end_turn"}


def no_network(*args, **kwargs):
    raise AssertionError("a refused call must never be sent")


class Isolated(unittest.TestCase):
    """Fake keys and a temporary spend log, so no test touches the real ones."""

    def setUp(self):
        keys = mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test", "CLOUD_QWEN_API_KEY": "test"})
        keys.start()
        self.addCleanup(keys.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "spend.csv"
        patch = mock.patch.object(spend, "SPEND_LOG", self.log)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def seed(self, cost, timestamp=None, budget="dev"):
        """Pretend this much was already spent, by default this month on the dev budget."""
        spend.log("ok", {"path": "claude", "model": "claude-sonnet-5-5", "budget": budget, "cost_usd": cost})
        if timestamp:
            rows = self.rows()
            rows[-1]["timestamp"] = timestamp
            with self.log.open("w", newline="") as f:
                writer = csv.DictWriter(f, spend.COLUMNS, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

    def rows(self):
        return list(csv.DictReader(io.StringIO(self.log.read_text())))


DEV_CAP = spend.CAP_USD["dev"]


class AdapterTest(Isolated):
    def test_dev_cap_breach_is_refused_and_never_sent(self):
        self.seed(DEV_CAP)
        with mock.patch.object(adapter, "post", no_network):
            for path in ("cloud", "claude"):
                with self.assertRaises(spend.CapReached):
                    adapter.call(path, HELLO)
        self.assertEqual([r["status"] for r in self.rows()], ["ok", "refused", "refused"])
        self.assertEqual([r["cost_usd"] for r in self.rows()[1:]], ["0", "0"])

    def test_worst_case_of_the_next_call_counts(self):
        self.seed(DEV_CAP - 0.01)        # under the cap, but 4,000 output tokens on Sonnet could cost $0.04
        with mock.patch.object(adapter, "post", no_network), self.assertRaises(spend.CapReached):
            adapter.call("claude", HELLO, max_tokens=4000)

    def test_demo_budget_counts_only_demo_rows(self):
        self.seed(DEV_CAP)        # dev is at its cap; a demo call is still allowed (D115)
        with mock.patch.object(adapter, "post", return_value=CLAUDE_OK):
            out = adapter.call("claude", HELLO, budget="demo")
        self.assertEqual(out["text"], "OK")
        self.assertAlmostEqual(out["cost_usd"], (1000 * 2.00 + 100 * 10.00) / 1e6)
        self.assertEqual(self.rows()[-1]["status"], "ok")
        self.seed(19.99, budget="demo")     # demo rows now near $20: the next demo call is refused
        with mock.patch.object(adapter, "post", no_network), self.assertRaises(spend.CapReached):
            adapter.call("claude", HELLO, budget="demo")

    def test_demo_rows_still_count_against_dev(self):
        self.seed(DEV_CAP, budget="demo")
        with mock.patch.object(adapter, "post", no_network), self.assertRaises(spend.CapReached):
            adapter.call("claude", HELLO)

    def test_last_months_spend_does_not_count(self):
        self.seed(19.99, timestamp="2000-01-31T23:59:59+00:00")
        with mock.patch.object(adapter, "post", return_value=CLAUDE_OK):
            adapter.call("claude", HELLO)

    def test_unpriced_paid_model_is_refused(self):
        with mock.patch.object(adapter, "post", no_network), self.assertRaises(spend.CapReached):
            adapter.call("cloud", HELLO, model="qwen/some-new-model")

    def test_local_is_free_and_not_capped(self):
        self.seed(20.00)
        reply = {"message": {"content": "OK"}, "prompt_eval_count": 12, "eval_count": 2, "done_reason": "stop"}
        with mock.patch.object(adapter, "post", return_value=reply), mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1"}):
            out = adapter.call("local", HELLO)
        self.assertEqual((out["cost_usd"], out["input_tokens"]), (0, 12))

    def test_local_asks_ollama_to_refuse_rather_than_cut(self):
        # D95: Ollama silently cut an over-long prompt to ~num_ctx/2 tokens; truncate/shift off makes it refuse or stop.
        reply = {"message": {"content": "OK"}, "prompt_eval_count": 12, "eval_count": 2, "done_reason": "stop"}
        with mock.patch.object(adapter, "post", return_value=reply) as post, \
                mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1"}):
            adapter.call("local", HELLO)
        body = post.call_args.args[1]
        self.assertEqual((body["truncate"], body["shift"], body["options"]["num_ctx"]), (False, False, adapter.NUM_CTX))

    def test_local_reply_that_runs_out_of_context_fails(self):
        cut = {"message": {"content": "1\n2\n3"}, "prompt_eval_count": 16300, "eval_count": 84, "done_reason": "length"}
        with mock.patch.object(adapter, "post", return_value=cut), mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1"}):
            with self.assertRaisesRegex(RuntimeError, "ran out of context"):
                adapter.call("local", HELLO, max_tokens=2048)

    def test_local_reply_that_reaches_max_tokens_is_not_a_context_error(self):
        full = {"message": {"content": "x"}, "prompt_eval_count": 7000, "eval_count": 2048, "done_reason": "length"}
        with mock.patch.object(adapter, "post", return_value=full), mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1"}):
            out = adapter.call("local", HELLO, max_tokens=2048)
        self.assertEqual(out["stop"], "length")

    def test_local_refuses_a_public_address(self):
        with mock.patch.dict("os.environ", {"OLLAMA_HOST": "http://8.8.8.8:11434"}), mock.patch.object(adapter, "post", no_network):
            with self.assertRaisesRegex(RuntimeError, "not a home-network address"):
                adapter.call("local", HELLO)
        self.assertEqual(self.rows()[-1]["status"], "error")

    def test_failed_call_is_logged_at_zero_cost(self):
        with mock.patch.object(adapter, "post", side_effect=RuntimeError("HTTP 400: bad")), self.assertRaises(RuntimeError):
            adapter.call("claude", HELLO)
        self.assertEqual((self.rows()[-1]["status"], self.rows()[-1]["cost_usd"]), ("error", "0"))


class RetryTest(unittest.TestCase):
    def http_error(self, code, headers=None):
        return urllib.error.HTTPError("https://x", code, "err", headers or {}, io.BytesIO(b"{}"))

    def test_overloaded_then_ok_is_retried_with_backoff(self):
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = b'{"ok": true}'
        with mock.patch("urllib.request.urlopen", side_effect=[self.http_error(529), self.http_error(429), ok]), \
                mock.patch("time.sleep") as sleep:
            self.assertEqual(adapter.post("https://x", {}, {}, 5), {"ok": True})
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    def test_retry_after_is_honoured(self):
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = b"{}"
        with mock.patch("urllib.request.urlopen", side_effect=[self.http_error(429, {"retry-after": "7"}), ok]), \
                mock.patch("time.sleep") as sleep:
            adapter.post("https://x", {}, {}, 5)
        sleep.assert_called_once_with(7.0)

    def test_gives_up_after_three_retries(self):
        with mock.patch("urllib.request.urlopen", side_effect=[self.http_error(500)] * 4) as urlopen, \
                mock.patch("time.sleep"), self.assertRaisesRegex(RuntimeError, "after 3 retries"):
            adapter.post("https://x", {}, {}, 5)
        self.assertEqual(urlopen.call_count, 4)

    def test_client_errors_are_not_retried(self):
        with mock.patch("urllib.request.urlopen", side_effect=[self.http_error(400)]) as urlopen, \
                mock.patch("time.sleep"), self.assertRaisesRegex(RuntimeError, "HTTP 400"):
            adapter.post("https://x", {}, {}, 5)
        self.assertEqual(urlopen.call_count, 1)


class ConversionTest(Isolated):
    def test_claude_tool_round_trip(self):
        """A tool call from Claude, then its result, become valid Anthropic messages on the next call."""
        content = [{"type": "thinking", "thinking": "", "signature": "s"},
                   {"type": "tool_use", "id": "tu_1", "name": "add", "input": {"a": 2, "b": 3}}]
        first = {"content": content, "usage": {"input_tokens": 10, "output_tokens": 5}, "stop_reason": "tool_use"}
        with mock.patch.object(adapter, "post", return_value=first):
            out = adapter.send_claude("claude-sonnet-5-5", HELLO, [], 100)
        self.assertEqual(out["tool_calls"], [{"id": "tu_1", "name": "add", "args": {"a": 2, "b": 3}}])
        history = [{"role": "system", "content": "Be brief."}, *HELLO, out["message"],
                   {"role": "tool", "tool_call_id": "tu_1", "content": "5"}]
        with mock.patch.object(adapter, "post", return_value=CLAUDE_OK) as post:
            adapter.send_claude("claude-sonnet-5-5", history, [], 100)
        body = post.call_args.args[1]
        self.assertEqual(body["system"], "Be brief.")
        self.assertEqual(body["messages"][1], {"role": "assistant", "content": content})
        self.assertEqual(body["messages"][2]["content"][0]["tool_use_id"], "tu_1")

    def test_local_tool_round_trip(self):
        """Ollama's tool-call arguments are objects; its own message goes back to it unchanged."""
        raw = {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "add", "arguments": {"a": 2}}}]}
        replies = [{"message": raw, "prompt_eval_count": 5, "eval_count": 3, "done_reason": "stop"},
                   {"message": {"role": "assistant", "content": "2"}, "prompt_eval_count": 6, "eval_count": 1}]
        with mock.patch.object(adapter, "post", side_effect=replies) as post, \
                mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1:11434"}):
            out = adapter.send_local("m", HELLO, [], 10)
            self.assertEqual(out["tool_calls"], [{"id": "call_0", "name": "add", "args": {"a": 2}}])
            adapter.send_local("m", [*HELLO, out["message"], {"role": "tool", "tool_call_id": "call_0", "content": "2"}], [], 10)
        self.assertEqual(post.call_args.args[1]["messages"][1], raw)

    def test_cloud_parses_json_text_arguments(self):
        msg = {"role": "assistant", "content": None,
               "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "add", "arguments": '{"a": 2, "b": 3}'}}]}
        reply = {"choices": [{"message": msg, "finish_reason": "tool_calls"}], "provider": "DeepInfra",
                 "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.000013}}
        with mock.patch.object(adapter, "post", return_value=reply) as post:
            out = adapter.call("cloud", HELLO, [{"name": "add", "parameters": {"type": "object"}}])
        self.assertEqual(out["tool_calls"], [{"id": "c1", "name": "add", "args": {"a": 2, "b": 3}}])
        self.assertEqual((out["text"], out["host"]), ("", "DeepInfra"))
        self.assertAlmostEqual(out["cost_usd"], (100 * 0.10 + 20 * 0.15) / 1e6)
        self.assertEqual(post.call_args.args[1]["provider"]["order"], ["deepinfra"])

if __name__ == "__main__":
    unittest.main()
