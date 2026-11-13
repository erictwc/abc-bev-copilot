# Every target here runs offline except bench, smoke, index, test-retrieval, smoke-agent, evals and judge. bench, index and test-retrieval
# call the box on the home network (OLLAMA_HOST, D34, D49); smoke calls the path it is given (D39, D40). A new outbound call needs a DECISIONS.md entry first.
PYTHON ?= python3
VENV := .venv
VPY := $(VENV)/bin/python   # targets that need duckdb (D47)

.PHONY: setup test-secret-scan data data-check corpus corpus-check bench test-adapter smoke db index test-tools test-retrieval test-loop smoke-agent evals evals-check judge

## setup: venv, dependencies, secret-scan hook, .env. Safe to run twice.
setup:
	@$(PYTHON) -c "import sys; v = sys.version_info; sys.exit(0 if v >= (3, 11) else f\"Python 3.11+ needed, found {v.major}.{v.minor}\")"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(VENV)/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
	@# Hooks are not cloned with a repo, so setup has to switch this one on.
	@git config core.hooksPath .githooks
	@test -f .env || { cp .env.example .env; echo "created .env from .env.example: fill in your keys"; }
	@echo "setup done: $$($(VENV)/bin/python --version), secret-scan hook on"

## test-secret-scan: fresh clone, make setup, then prove fake keys are blocked.
test-secret-scan:
	@$(PYTHON) .githooks/test_pre_commit.py

## data: write the six v1 tables to data/csv/ with SHA256SUMS. Standard library only (D18).
data:
	@$(PYTHON) data/generate.py --out data/csv

## data-check: generate twice into temp folders; both runs and data/csv/ must be byte-identical.
data-check:
	@tmp=$$(mktemp -d) && trap 'rm -rf "$$tmp"' EXIT && \
	$(PYTHON) data/generate.py --out "$$tmp/a" >/dev/null && \
	$(PYTHON) data/generate.py --out "$$tmp/b" >/dev/null && \
	diff -r "$$tmp/a" "$$tmp/b" && diff -r "$$tmp/a" data/csv && \
	echo "data-check: two runs and data/csv/ are byte-identical" && cat data/csv/SHA256SUMS

## corpus: write the 20 product sheets to docs_corpus/ from sku_master. Standard library only (D23).
corpus:
	@$(PYTHON) docs_corpus/make_sheets.py

## corpus-check: regenerate sheets into a temp folder, compare with docs_corpus/, then check every header (D22).
corpus-check:
	@tmp=$$(mktemp -d) && trap 'rm -rf "$$tmp"' EXIT && \
	$(PYTHON) docs_corpus/make_sheets.py --out "$$tmp" >/dev/null && \
	for f in "$$tmp"/*.md; do cmp -s "$$f" "docs_corpus/$$(basename "$$f")" || { echo "differs: $$(basename "$$f")"; exit 1; }; done && \
	echo "corpus-check: generated sheets match docs_corpus/ byte for byte" && \
	$(PYTHON) docs_corpus/make_sheets.py --check

## bench: prefill and decode tokens/s from Ollama on the box, appended to bench/results.csv (T3, D34-D38).
bench:
	@$(PYTHON) bench/run_bench.py

## test-adapter: offline tests of the model adapter: cap, spend log, retries, message conversion (T4).
test-adapter:
	@$(PYTHON) -m unittest agent.test_adapter

## smoke: one tool-call round trip per path, e.g. make smoke PATHS="cloud claude". Paid paths cost under a cent.
PATHS ?= local cloud claude
smoke:
	@for p in $(PATHS); do $(PYTHON) agent/smoke.py $$p || exit 1; done

## db: build data/abc.duckdb from data/csv/ with explicit column types; gitignored (T5, D55).
db:
	@$(VPY) -m agent.index db

## index: chunk docs_corpus/, embed on the box, write data/docs.duckdb; gitignored (T5, D48-D50).
index:
	@$(VPY) -m agent.index docs

## test-tools: offline tests of run_sql's guard rails, chunking and search_docs, with fake embeddings (T5).
test-tools:
	@$(VPY) -m unittest agent.test_tools

## test-retrieval: five hand-picked questions must return the right DOC-ID first; needs the box and make index (T5).
test-retrieval:
	@$(VPY) -m unittest -v agent.test_retrieval

## test-loop: offline tests of the agent loop with a fake model and fake tools (T6).
test-loop:
	@$(VPY) -m unittest agent.test_loop

## smoke-agent: the ten smoke questions through the agent loop (T6, D67); needs the box, and the key for paid paths.
SMOKE_PATH ?= claude
smoke-agent:
	@$(VPY) -m agent.smoke_agent --path $(SMOKE_PATH)

## evals: evals/cases.toml through one path, results to evals/results/ (T7, D72-D74); needs the box, and the key for
## paid paths. e.g. make evals EVAL_PATH=cloud ONLY=E01,E02
EVAL_PATH ?= claude
EVAL_MODEL ?=
ONLY ?=
evals:
	@$(VPY) -m evals.run --path $(EVAL_PATH) $(if $(EVAL_MODEL),--name $(EVAL_MODEL)) $(if $(ONLY),--only $(ONLY))

## judge: judge an earlier run with claude-opus-5-5 into <run>_judged.{csv,md,jsonl} (T9, D84); needs the key.
## e.g. make judge RUN=evals/results/2026-11-13T2207Z_cloud_qwen-qwen3.5-9b.jsonl
RUN ?=
judge:
	@$(VPY) -m evals.judge $(RUN)

## evals-check: offline: validate evals/cases.toml, then the scorer, runner and judge tests with fake results (D74).
evals-check:
	@$(VPY) -m evals.score && $(VPY) -m unittest evals.test_score evals.test_judge
