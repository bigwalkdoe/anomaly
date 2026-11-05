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
	alembic -c packages/core/alembic.ini upgrade head
