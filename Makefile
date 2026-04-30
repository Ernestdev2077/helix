.PHONY: help setup up down logs restart clean \
	backend-shell backend-migrate backend-migrations backend-superuser backend-test \
	agents-shell frontend-shell frontend-install

help:
	@echo "Common commands:"
	@echo "  make setup            — copy .env.example, install deps, build images"
	@echo "  make up               — start all services (docker compose)"
	@echo "  make down             — stop all services"
	@echo "  make logs             — tail logs from all services"
	@echo ""
	@echo "Backend (Django):"
	@echo "  make backend-migrate      — run migrations"
	@echo "  make backend-migrations   — create new migrations"
	@echo "  make backend-superuser    — create Django superuser"
	@echo "  make backend-shell        — bash inside backend container"
	@echo "  make backend-test         — run pytest"
	@echo ""
	@echo "Agents (FastAPI):"
	@echo "  make agents-shell         — bash inside agents container"
	@echo ""
	@echo "Frontend (Vue):"
	@echo "  make frontend-install     — npm install"
	@echo "  make frontend-shell       — sh inside frontend container"

setup:
	@[ -f .env ] || cp .env.example .env
	@echo ".env ready. Now run: make up"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

clean:
	docker compose down -v

backend-shell:
	docker compose exec backend bash

backend-migrate:
	docker compose exec backend python manage.py migrate

backend-migrations:
	docker compose exec backend python manage.py makemigrations

backend-superuser:
	docker compose exec backend python manage.py createsuperuser

backend-test:
	docker compose exec backend pytest

agents-shell:
	docker compose exec agents bash

frontend-install:
	docker compose exec frontend npm install

frontend-shell:
	docker compose exec frontend sh
