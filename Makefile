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

.PHONY: smoke ci-local pr
smoke:
	python3 scripts/smoke.py

ci-local:
	bash scripts/ci_local.sh

pr:
	bash scripts/pr.sh

.PHONY: db-upgrade
db-upgrade:
	bash scripts/db_upgrade_local.sh

.PHONY: workspace-init
workspace-init:
	bash scripts/workspace_init.sh

.PHONY: operational-check
operational-check:
	@echo "Operational Core assessment is available after an authorized database upgrade."
	@echo "Run make validate and verify in the browser at the local workspace."
