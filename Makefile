.PHONY: seed run-once api web test test-frontend install

# ── Install ────────────────────────────────────────────────────────────────
install:
	pip install -e ".[dev]"

# ── Tests ─────────────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v
	$(MAKE) test-frontend

# ── Frontend tests (vitest + design lint) ──────────────────────────────────
test-frontend:
	cd web && npm run test
	bash scripts/design-lint.sh

# ── Data ──────────────────────────────────────────────────────────────────
seed:
	python scripts/seed_synthetic.py

run-once:
	python scripts/run_once.py

# ── API server ─────────────────────────────────────────────────────────────
api:
	uvicorn apix.api:app --reload --host 0.0.0.0 --port 8000

# ── Frontend ───────────────────────────────────────────────────────────────
web:
	cd web && npm run dev
