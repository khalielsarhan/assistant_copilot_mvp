COMPOSE=docker compose

.PHONY: setup up down restart build migrate shell createsuperuser logs test check status

setup:
	test -f .env || cp .env.example .env
	$(COMPOSE) up --build -d
	$(COMPOSE) exec web python manage.py migrate

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) up --build -d

migrate:
	$(COMPOSE) exec web python manage.py migrate

shell:
	$(COMPOSE) exec web python manage.py shell

createsuperuser:
	$(COMPOSE) exec web python manage.py createsuperuser

logs:
	$(COMPOSE) logs -f web celery celery-beat

test:
	$(COMPOSE) exec web python manage.py test

check:
	$(COMPOSE) exec web python manage.py check

status:
	$(COMPOSE) ps
