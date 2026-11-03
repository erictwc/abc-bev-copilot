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

> **Status:** synthetic data (T1). `make data` rebuilds the tables in `data/csv/`; nothing else works yet.

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

*Accuracy, latency and cost per question for each model path: T10. Every number
here comes from a committed results file.*

| Path | Accuracy | Latency | Cost / question |
|---|---|---|---|
| local Qwen | not run | not run | not run |
| cloud Qwen | not run | not run | not run |
| Claude | not run | not run | not run |

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
