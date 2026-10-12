.PHONY: up down health migrate
up:
	docker compose up -d --build
down:
	docker compose down
health:
	curl -fsS http://localhost:8000/health
migrate:
	bash scripts/migrate.sh
