.PHONY: up down test lint typecheck migrate

up:
	docker compose up -d

down:
	docker compose down

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy packages apps

migrate:
	cd packages/core && alembic upgrade head