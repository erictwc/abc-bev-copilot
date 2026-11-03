# Every target here runs offline except bench, which calls the box on the home network
# (OLLAMA_HOST, D34). A new outbound call needs a DECISIONS.md entry first.
PYTHON ?= python3
VENV := .venv

.PHONY: setup test-secret-scan data data-check corpus corpus-check bench

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
