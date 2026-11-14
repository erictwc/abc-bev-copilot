"""Offline tests of the hosted demo (T14): no model is called and no key is needed.

The two checks in T14's "done when": a loop of repeated requests is stopped by the rate limit, and by the
spend cap. The cap test runs the real agent.loop.ask() and adapter against a spend log seeded near the
demo cap, with the network patched to fail, so a request that got through would show up as an error.
Run with: python -m unittest demo.test_server
"""
import json, tempfile, threading, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from agent import adapter, loop, spend
from demo import server


def fake_ask(question, path, budget):
    assert budget == "demo"
    return {"question": question, "path": path, "model": "fake", "answer": "ok", "confidence": "high",
            "flags": [], "evidence": {"sql": [], "passages_cited": [], "passages_retrieved": []},
            "stopped": "answer", "steps": 1, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "latency_s": 0.1}


class Demo(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        for target, attr, value in [(server, "REQUEST_LOG", self.dir / "requests.jsonl"),
                                    (spend, "SPEND_LOG", self.dir / "spend.csv"),
                                    (loop, "RUN_LOG", self.dir / "runs.jsonl")]:
            p = mock.patch.object(target, attr, value)
            p.start()
            self.addCleanup(p.stop)
        env = mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test", "CLOUD_QWEN_API_KEY": "test",
                                             "DEMO_LIVE": "on", "DEMO_PROXY_HOPS": "1"})
        env.start()
        self.addCleanup(env.stop)

    def start(self, ask=fake_ask, limiter=None):
        handler = server.make_handler(limiter or server.Limiter(), server.latest_local_run(), ask=ask)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def post(self, question="How is fill rate defined?", model="claude", ip="203.0.113.7"):
        req = urllib.request.Request(self.base + "/api/ask", json.dumps({"question": question, "model": model}).encode(),
                                     {"Content-Type": "application/json", "X-Forwarded-For": ip})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return r.read()

    def log(self):
        return [json.loads(l) for l in server.REQUEST_LOG.read_text().splitlines()]

    def test_a_loop_of_requests_is_stopped_by_the_rate_limit(self):
        self.start()
        codes = [self.post()[0] for _ in range(12)]
        self.assertEqual(codes, [200] * 5 + [429] * 7)
        self.assertEqual(self.post(ip="198.51.100.9")[0], 200)        # another visitor still gets through
        entries = self.log()
        self.assertEqual(sum(e["admitted"] for e in entries), 6)
        self.assertNotIn("203.0.113.7", server.REQUEST_LOG.read_text())   # IPs are hashed

    def test_a_spoofed_forwarded_header_does_not_dodge_the_limit(self):
        self.start()
        codes = [self.post(ip=f"10.0.0.{i}, 203.0.113.7")[0] for i in range(7)]
        self.assertEqual(codes, [200] * 5 + [429] * 2)

    def test_a_loop_of_requests_is_stopped_by_the_spend_cap(self):
        spend.log("ok", {"path": "claude", "model": "claude-sonnet-5-5", "budget": "demo", "cost_usd": 19.995})
        self.start(ask=loop.ask)

        def no_network(*a, **k):
            raise AssertionError("a model call was sent past the cap")
        with mock.patch.object(adapter, "post", no_network):
            for i in range(3):
                status, body = self.post(ip=f"198.51.100.{i}")
                self.assertEqual(status, 200)
                self.assertEqual(body["stopped"], "spend_cap")
                self.assertIn("demo budget is used up", body["answer"])
        statuses = [r.split(",")[4] for r in spend.SPEND_LOG.read_text().splitlines()[1:]]
        self.assertEqual(statuses, ["ok", "refused", "refused", "refused"])

    def test_site_daily_total_and_concurrency(self):
        limiter = server.Limiter(site_today=server.SITE_PER_DAY - 1)
        self.assertIsNone(limiter.acquire("a"))
        self.assertEqual(limiter.acquire("a")[0], 429)          # still running
        limiter.release("a")
        self.assertEqual(limiter.acquire("b")[0], 429)          # site total reached
        busy = server.Limiter()
        self.assertIsNone(busy.acquire("a"))
        self.assertIsNone(busy.acquire("b"))
        self.assertEqual(busy.acquire("c")[0], 503)

    def test_windows_reopen_with_time(self):
        clock = [1_000_000.0]
        limiter = server.Limiter(clock=lambda: clock[0])
        for _ in range(5):
            self.assertIsNone(limiter.acquire("a"))
            limiter.release("a")
        self.assertEqual(limiter.acquire("a")[0], 429)
        clock[0] += 601
        self.assertIsNone(limiter.acquire("a"))

    def test_bad_requests_and_the_kill_switch(self):
        self.start()
        self.assertEqual(self.post(model="local")[0], 400)
        self.assertEqual(self.post(question="")[0], 400)
        self.assertEqual(self.post(question="x" * 501)[0], 400)
        with mock.patch.dict("os.environ", {"DEMO_LIVE": "off"}):
            self.assertEqual(self.post()[0], 503)
        self.assertFalse(any(e["admitted"] for e in self.log()))

    def test_page_config_and_replays_carry_no_keys(self):
        self.start()
        page, config, replays = self.get("/"), self.get("/api/config"), self.get("/api/replays")
        self.assertIn(b"Replay, not live", page)
        for blob in (page, config, replays):
            self.assertNotIn(b"ANTHROPIC_API_KEY", blob)
            self.assertNotIn(b"sk-", blob)
        cases = json.loads(replays)["cases"]
        self.assertEqual(len(cases), 40)
        self.assertTrue(all(c["result"]["path"] == "local" for c in cases))


if __name__ == "__main__":
    unittest.main()
