.PHONY: dev-backend dev-frontend test migrate

dev-backend:
	uv run uvicorn main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	uv run pytest

migrate:
	uv run alembic upgrade head
