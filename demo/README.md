# The hosted demo (T14)

One web page for people who will not clone the repo: a question box and a model dropdown.

- **Claude Sonnet 5.5** and **cloud Qwen 3.5 9B** answer live, through the same `agent.loop.ask()` as the
  CLI, on the `demo` budget: $20 a month counted on demo calls only (D115).
- **Local Qwen 3.5 9B** is never called. The page shows its recorded answers to the 40 eval questions
  from the newest committed local run in `evals/results/`, labelled as replays with their eval result.
- Keys stay on the server. The browser gets answers, evidence and costs, nothing else.
- Retrieval runs on the container's own Ollama with the same embedding model and version as the
  GEEKOM box, on loopback (D112). The box is not involved and is never reachable from the internet.

## Limits (D116)

Constants in `demo/server.py`, so changing one is a reviewed commit:

| Limit | Value |
|---|---|
| Live questions per visitor | 1 at a time, 5 per 10 minutes, 20 per day |
| Live questions for the whole site | 100 per day (UTC), 2 running at once |
| Question length | 500 characters |
| Spend | the adapter's `demo` cap, $20 a month, counted on demo rows only |
| Kill switch | `DEMO_LIVE=off` pauses live answers; replays still work |

Every live request, admitted or refused, is a line in `logs/demo_requests.jsonl`: time, hashed IP,
model, question, outcome, cost and latency. On the Space, `logs/` is a link to a Storage Bucket mounted
at `/data`, so the spend log, and with it the cap, survives a restart. Without a writable `/data`, the container
starts with live answers off.

## Run it locally

```bash
OLLAMA_HOST=http://<box address>:11434 make demo
```

Then open http://127.0.0.1:7860. Live answers need the keys in `.env`; replays need nothing.

```bash
make test-demo
```

Offline tests: a loop of repeated requests stopped by the rate limit and by the spend cap, a spoofed
`X-Forwarded-For`, the site total, the concurrency limit, the kill switch, and replays with no keys.

## Deploy to Hugging Face Spaces (D113)

Eric's steps. Each one is in his own accounts.

1. **Demo-only API keys with provider-side limits**, a backstop that holds even if the app's log is lost.
   Anthropic: a separate workspace with a monthly spend limit and its own key. OpenRouter: a new key
   with a credit limit. The two limits add up to $20 or less.
2. **Create the Space**: Docker SDK, Blank template, CPU Basic, public. Docker Spaces on CPU Basic now
   need a Hugging Face **Pro** subscription (about $9 a month). Under Storage Buckets,
   create a bucket and attach it **read-write at `/data`** (confirm the price on the settings page).
   Hugging Face retired the old persistent-storage disk in 2026; a bucket is its replacement. Without
   a writable `/data` the Space still runs, with replays only.
3. **Space secrets** (Settings, Variables and secrets): `ANTHROPIC_API_KEY`, `CLOUD_QWEN_API_KEY` (the
   demo keys from step 1), and `DEMO_LOG_SALT` (any long random string, so hashed IPs stay stable across
   restarts).
4. **Push the code**: commit, then
   ```bash
   git clone https://huggingface.co/spaces/<user>/<space> ../space
   sh demo/build_space.sh ../space
   cd ../space && git add -A && git commit -m "Demo from <commit>" && git push
   ```
   Git asks for your Hugging Face username and a **write** access token as the password.
   `build_space.sh` packs the committed tree at HEAD (never `.env`, `logs/`, the local `.duckdb` files,
   or the memo `.docx`, since the Hub refuses plain-git binary files) and puts the Dockerfile and the
   Space's README at the root.
5. The build builds both DuckDB stores, pulls `qwen3-embedding:0.6b`, and runs `agent.test_retrieval`
   and `demo.test_server`. **If retrieval differs from the box, the build fails.**
6. **After the first live question**, check that `forwarded` in `logs/demo_requests.jsonl` is 1. If the
   host's proxy adds more than one `X-Forwarded-For` entry, set the Space variable `DEMO_PROXY_HOPS` to
   that number, or every visitor shares one rate-limit bucket.
7. **Check that the cap survives a restart.** Ask a second question, restart the Space (Settings), and
   check that `logs/spend.csv` still has both rows. The spend log is appended to, and how a bucket
   mount handles appends is not documented; if rows go missing, live answers must stay off
   (`DEMO_LIVE=off`) until the log lives somewhere else.

The Space sleeps after about 48 hours with no visitors and wakes on the next visit (a minute or two).
