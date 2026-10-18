.PHONY: test test-integration lint up down logs smoke presentation

test:
	pytest -q

test-integration:
	ci/integration.sh

lint:
	ruff check src tests

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

# HTTP checks against a stack that is already up (the pipeline's last stage).
smoke:
	ci/smoke.sh

# docs/presentation/*.md -> the matching .pdf (English + Portuguese decks)
presentation:
	python3 docs/presentation/build.py
