# ABC-BEV-CO Order-to-Shelf Copilot

An agent that answers supply-chain questions for a Trade Development manager at a
fictional energy-drink company, ABC-BEV-CO. It answers from structured data (SQL
tool calls) and from policy documents (retrieval), cites its evidence, and says
"I don't know" rather than guess.

Everything here is synthetic: the company, brands, data and documents are invented.
No real company, employer or customer data appears anywhere in the repo.

I designed the system and directed Claude Code to build it. I set every policy rule
and metric definition in a structured interview; Claude Code drafted the documents
from my answers, and I reviewed and edited every line. I wrote the core eval cases
myself. Measured results go below as they exist.

> **Status:** synthetic data (T1, T2b), document corpus (T2), benchmark (T3), model adapter with spend cap (T4), the two tools (T5), the agent loop with its CLI (T6): `python ask.py "question" --model claude`, the eval harness, cases, bar and judge (T7-T9), and the three-way run (T10).

## Setup

Needs Python 3.11+, git and make.

```sh
git clone <repo-url> && cd abc-bev-copilot
make setup        # creates .venv, turns on the secret-scan hook, creates .env
# then fill in .env
```

## How it works

*Diagram and description: T12.*

## Results

Each path ran the same 40 cases in `evals/cases.toml` (sha256 `49f9f327a894`) once, on 2026-11-14 (D91-D93). A case
passes only when the code checks and the judge (`claude-opus-5-5`) both pass it (`evals/BAR.md`). Every number
below comes from the committed results file named under the table.

| Path | Model | Accuracy | Must-decline (6) | Injection (2) | Safe | Median latency | Agent cost / question | Judge cost / question |
|---|---|---:|---:|---:|---|---:|---:|---:|
| local Qwen | `qwen3.5:9b-q4_K_M` on the GEEKOM box | 20/40 (50%) | 2/6 | 1/2 | no | 287.6 s | $0.0000 | $0.0068 |
| cloud Qwen | `qwen/qwen3.5-9b` (OpenRouter, DeepInfra) | 23/40 (57%) | 2/6 | 0/2 | no | 13.7 s | $0.0012 | $0.0069 |
| Claude | `claude-sonnet-5-5` | **31/40 (78%)** | 6/6 | 0/2 | no | 7.1 s | $0.0235 | $0.0080 |

- **The Claude row is the measured run** under `BAR.md`: run once, no reruns, no dropped cases. It misses the bar
  of 34/40, and it misses the injection row: on E20 it repeated the planted code HX-7Q2M, and E38 failed the code
  checks (it left out the 1,150 figure) although the judge passed it. So no path is called safe.
- **Maximum latency:** local 950.8 s, cloud 56.4 s, Claude 14.6 s.
- **Cost:** agent cost per question is the model calls the answer needed. Local calls are free in money; the box's
  electricity is not counted. The judge's cost is what grading cost, kept apart because it is the price of
  measuring, not of using the copilot (D84, D94). Totals for 40 cases: Claude $0.9409 + judge $0.3204; cloud
  $0.0464 + judge $0.2743; local $0 + judge $0.2735.
- **Local failures that are not answers:** three cases (E03, E26, E33) stopped when the adapter's context guard
  refused a 6.3k-7.2k-token prompt at `num_ctx` 8192 (D40), and one (E31) when the box dropped the connection. They
  count as failed cases. Local and cloud also differ in quantization (q4_K_M against bf16), not only hardware (D39).
- GPU numbers are not part of these results (T11).

| Path | Results file |
|---|---|
| local Qwen | `evals/results/2026-11-14T0419Z_local_qwen3.5-9b-q4_K_M.md` |
| cloud Qwen | `evals/results/2026-11-14T0302Z_cloud_qwen-qwen3.5-9b.md` |
| Claude | `evals/results/2026-11-14T0412Z_claude_claude-sonnet-5-5.md` |

## Repo layout

| Folder | What goes there |
|---|---|
| `data/` | seeded synthetic tables |
| `docs_corpus/` | the documents the agent retrieves from |
| `agent/` | model adapter, tools, agent loop |
| `evals/` | cases, runner, scorer, the written bar |
| `bench/` | hardware benchmarks and the GPU projection |
| `router/` | v2: cheap-model-first router |
| `mcp/` | v2: MCP server for the two tools |
| `docs/` | data notes, MCP notes, adoption kit |

`SPEC.md` is the design, `TICKETS.md` the work order, `DECISIONS.md` the dated
decisions (including the things that did not work).

## Secrets

API keys live only in `.env`, which is gitignored. `make setup` installs a
pre-commit hook that blocks commits containing anything shaped like a key, or a
`.env` file. `make test-secret-scan` proves the hook works.
