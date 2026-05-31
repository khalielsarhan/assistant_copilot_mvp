COMPOSE=docker compose
PROD_COMPOSE=$(COMPOSE) -f docker-compose.prod.yml --env-file .env.production

.PHONY: setup up down restart recreate build migrate shell createsuperuser logs test check status prod-up prod-down prod-migrate prod-logs prod-status prod-shell

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

recreate:
	$(COMPOSE) up -d --force-recreate web celery celery-beat

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

prod-up:
	$(PROD_COMPOSE) up --build -d

prod-down:
	$(PROD_COMPOSE) down

prod-migrate:
	$(PROD_COMPOSE) exec web python manage.py migrate
	$(PROD_COMPOSE) exec web python manage.py collectstatic --noinput

prod-logs:
	$(PROD_COMPOSE) logs -f web telegram-poller celery celery-beat

prod-status:
	$(PROD_COMPOSE) ps

prod-shell:
	$(PROD_COMPOSE) exec web python manage.py shell
