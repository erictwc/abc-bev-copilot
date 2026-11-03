# Every target here runs offline. A new outbound call needs a DECISIONS.md entry first.
PYTHON ?= python3
VENV := .venv

.PHONY: setup test-secret-scan data data-check

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

## data: write the five v1 tables to data/csv/ with SHA256SUMS. Standard library only (D18).
data:
	@$(PYTHON) data/generate.py --out data/csv

## data-check: generate twice into temp folders; both runs and data/csv/ must be byte-identical.
data-check:
	@tmp=$$(mktemp -d) && trap 'rm -rf "$$tmp"' EXIT && \
	$(PYTHON) data/generate.py --out "$$tmp/a" >/dev/null && \
	$(PYTHON) data/generate.py --out "$$tmp/b" >/dev/null && \
	diff -r "$$tmp/a" "$$tmp/b" && diff -r "$$tmp/a" data/csv && \
	echo "data-check: two runs and data/csv/ are byte-identical" && cat data/csv/SHA256SUMS
