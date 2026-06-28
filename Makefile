PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/python -m pip

.PHONY: setup check smoke e2e test-python test-frontend build-frontend docs-check architecture-check

setup:
	test -x .venv/bin/python || python3 -m venv .venv
	$(PIP) install -r requirements.txt
	npm --registry=https://registry.npmjs.org/ --prefix frontend ci
	npm --prefix frontend exec -- playwright install chromium

test-python:
	$(PYTHON) -m pytest -q

test-frontend:
	npm --prefix frontend test -- --run

build-frontend:
	npm --prefix frontend run build

docs-check:
	$(PYTHON) scripts/check_docs.py

architecture-check:
	$(PYTHON) -m pytest -q tests/test_architecture.py

check: test-python test-frontend build-frontend docs-check

smoke:
	$(PYTHON) scripts/smoke_dashboard.py

e2e: build-frontend
	npm --prefix frontend run e2e
