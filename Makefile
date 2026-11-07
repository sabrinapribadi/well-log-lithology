.PHONY: env lint test build-test hover-test preview evidence p0 p1 p2 page-data pipeline

# Environments live outside OneDrive (shared by all portfolio projects)
PY ?= $(HOME)/.venvs/portfolio/bin/python
NODE_DIR ?= $(HOME)/.portfolio-node

env:
	uv venv $(HOME)/.venvs/portfolio --python 3.12 --allow-existing && VIRTUAL_ENV=$(HOME)/.venvs/portfolio uv pip install -r requirements.txt
	mkdir -p $(NODE_DIR) && cd $(NODE_DIR) && (test -f package.json || echo '{"name": "portfolio-node", "private": true}' > package.json) && npm i -q puppeteer-core@23

lint:
	$(PY) -m ruff check src scripts tests

test:
	$(PY) -m pytest -q tests

# Pipeline (needs WLL_DATA_DIR: set -a; . ./.env; set +a)
p0:
	$(PY) scripts/force_ingest.py && $(PY) scripts/kgs_inventory.py && $(PY) scripts/p0_report.py && $(PY) scripts/reference_floors.py

p1:
	$(PY) scripts/p1_baseline.py

p2:
	$(PY) scripts/p2_model_choice.py

page-data:
	$(PY) scripts/export_page_data.py

pipeline: p0 p1 p2 page-data

evidence:
	$(PY) scripts/evidence.py

build-test:
	cd tests/browser && NODE_PATH=$(NODE_DIR)/node_modules node build_test.js $(CURDIR)/docs/build.html /tmp | grep -E "FAIL|build-page checks"

hover-test:
	cd tests/browser && mkdir -p /tmp/og2-shots && NODE_PATH=$(NODE_DIR)/node_modules node hover_test.js $(CURDIR)/docs/index.html /tmp/og2-shots

# Share-preview images for LinkedIn and other link cards (rule R18)
preview:
	mkdir -p docs/assets && cd tests/browser && NODE_PATH=$(NODE_DIR)/node_modules node preview.js $(CURDIR)/docs/index.html $(CURDIR)/docs/assets/preview.png && NODE_PATH=$(NODE_DIR)/node_modules node preview.js $(CURDIR)/docs/build.html $(CURDIR)/docs/assets/preview-build.png
