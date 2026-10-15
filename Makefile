.PHONY: env test build-test hover-test evidence p0 p1 p2 page-data pipeline

# Environments live outside OneDrive (shared by all portfolio projects)
PY ?= $(HOME)/.venvs/portfolio/bin/python
NODE_DIR ?= $(HOME)/.portfolio-node

env:
	uv venv $(HOME)/.venvs/portfolio --python 3.12 --allow-existing && VIRTUAL_ENV=$(HOME)/.venvs/portfolio uv pip install -r requirements.txt
	mkdir -p $(NODE_DIR) && cd $(NODE_DIR) && (test -f package.json || echo '{"name": "portfolio-node", "private": true}' > package.json) && npm i -q puppeteer-core@23

test:
	$(PY) -m pytest -q tests

evidence:
	$(PY) scripts/evidence.py

build-test:
	cd tests/browser && NODE_PATH=$(NODE_DIR)/node_modules node build_test.js $(CURDIR)/docs/build.html /tmp | grep -E "FAIL|build-page checks"

hover-test:
	cd tests/browser && mkdir -p /tmp/og2-shots && NODE_PATH=$(NODE_DIR)/node_modules node hover_test.js $(CURDIR)/docs/index.html /tmp/og2-shots
