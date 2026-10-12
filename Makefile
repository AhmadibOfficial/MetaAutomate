.PHONY: up down health migrate
up:
	docker compose up -d --build
down:
	docker compose down
health:
	curl -fsS http://localhost:8000/health
migrate:
	bash scripts/migrate.sh

.PHONY: validate
validate:
	@echo "Running MetaAutomate automated tests..."
	docker compose run --rm -T -v "$(CURDIR):/workspace:ro" -w /workspace -e PYTHONPATH=/workspace/apps/api api python -m pytest -q -p no:cacheprovider --import-mode=importlib apps/api/tests tests/
