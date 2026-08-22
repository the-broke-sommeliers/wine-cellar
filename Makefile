VIRTUAL_ENV ?= .venv
NODE_BIN = node_modules/.bin
SOURCE_DIRS = wine_cellar tests
ARGUMENTS=$(filter-out $(firstword $(MAKECMDGOALS)), $(MAKECMDGOALS))

.PHONY: all
all: help

.PHONY: install
install:
	npm install --no-save
	npm run build
	uv sync
	$(VIRTUAL_ENV)/bin/python3 manage.py migrate

.PHONY: clean
clean:
	if [ -d node_modules ]; then rm -rf node_modules; fi
	if [ -d .venv ]; then rm -rf .venv; fi

.PHONY: server
server:
	$(VIRTUAL_ENV)/bin/python3 manage.py runserver 8003

.PHONY: watch
watch:
	trap 'kill %1' KILL; \
	npm run watch & \
	$(VIRTUAL_ENV)/bin/python3 manage.py runserver 8003

.PHONY: fixtures
fixtures:
	$(VIRTUAL_ENV)/bin/python3 manage.py loaddata fixtures/user.json
	$(VIRTUAL_ENV)/bin/python3 manage.py loaddata fixtures/grapes.json
	$(VIRTUAL_ENV)/bin/python3 manage.py loaddata fixtures/region_and_appellation.json
	$(VIRTUAL_ENV)/bin/python3 manage.py loaddata fixtures/wines.json
	$(VIRTUAL_ENV)/bin/python3 manage.py loaddata fixtures/stock.json

.PHONY: docker-server
docker-server:
	if [ ! -f .env.dev ]; then cp .env.dev-sample .env.dev; fi
	docker compose up --build

.PHONY: docker-fixtures
docker-fixtures:
	docker compose exec web python3 manage.py loaddata fixtures/region_and_appellation.json
	docker compose exec web python3 manage.py loaddata fixtures/grapes.json
	docker compose exec web python3 manage.py loaddata fixtures/wines.json
	docker compose exec web python3 manage.py loaddata fixtures/stock.json

.PHONY: pytest
pytest:
	$(VIRTUAL_ENV)/bin/py.test --reuse-db

.PHONY: pytest-lastfailed
pytest-lastfailed:
	$(VIRTUAL_ENV)/bin/py.test --reuse-db --last-failed

.PHONY: pytest-clean
pytest-clean:
	if [ -f test_db.sqlite3 ]; then rm test_db.sqlite3; fi
	$(VIRTUAL_ENV)/bin/py.test

.PHONY: coverage
coverage:
	$(VIRTUAL_ENV)/bin/py.test --reuse-db --cov --cov-report=html

.PHONY: pytest-postgres
pytest-postgres:
	docker rm -f wine_cellar_test_db > /dev/null 2>&1 || true
	docker run -d --rm --name wine_cellar_test_db \
		-e POSTGRES_USER=wine_cellar_test \
		-e POSTGRES_PASSWORD=wine_cellar_test \
		-e POSTGRES_DB=wine_cellar_test \
		-p 5433:5432 \
		postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b > /dev/null
	trap 'docker stop wine_cellar_test_db > /dev/null' EXIT; \
	until docker exec wine_cellar_test_db pg_isready -U wine_cellar_test > /dev/null 2>&1; do sleep 1; done; \
	SQL_ENGINE=django.db.backends.postgresql \
	SQL_DATABASE=wine_cellar_test \
	SQL_USER=wine_cellar_test \
	SQL_PASSWORD=wine_cellar_test \
	SQL_HOST=localhost \
	SQL_PORT=5433 \
	$(VIRTUAL_ENV)/bin/py.test $(ARGUMENTS)

.PHONY: e2e
e2e:
	$(VIRTUAL_ENV)/bin/playwright install chromium
	# Playwright's sync API marks the calling thread as having a running asyncio
	# event loop (playwright/_impl/_sync_base.py) and never clears it, which makes
	# Django's async-safety check (SynchronousOnlyOperation) misfire on ORM calls
	# during test-db setup even though nothing here is actually async.
	DJANGO_ALLOW_ASYNC_UNSAFE=1 $(VIRTUAL_ENV)/bin/py.test -m e2e --reuse-db

.PHONY: lint
lint:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/isort --diff -c $(SOURCE_DIRS) ||  EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/flake8 $(SOURCE_DIRS) --exclude migrations,settings ||  EXIT_STATUS=$$?; \
	npm run lint ||  EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/python manage.py makemigrations --dry-run --check --noinput || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: lint-quick
lint-quick:
	EXIT_STATUS=0; \
	npm run lint-staged ||  EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/python manage.py makemigrations --dry-run --check --noinput || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: lint-js-fix
lint-js-fix:
	EXIT_STATUS=0; \
	npm run lint-fix || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

# Use with caution, the automatic fixing might produce bad results
.PHONY: lint-html-fix
lint-html-fix:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/djlint $(ARGUMENTS) --reformat --profile=django --ignore=H030,H031,T002 || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: lint-html
lint-html:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/djlint $(ARGUMENTS) --profile=django --ignore=H030,H031,T002 || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: lint-py
lint-py:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/black $(ARGUMENTS) || EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/isort $(ARGUMENTS) --filter-files || EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/flake8 $(ARGUMENTS) || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: po
po:
	$(VIRTUAL_ENV)/bin/python manage.py makemessages --all --no-obsolete -d django --extension html,email,py --ignore '.venv/*' --ignore 'node_modules/*' --ignore 'build/*' --ignore "wine_cellar/static/**"
	$(VIRTUAL_ENV)/bin/python manage.py makemessages --all --no-obsolete -d djangojs --extension js,jsx,ts,tsx --ignore '.venv/*' --ignore 'node_modules/*' --ignore 'build/*' --ignore "wine_cellar/static/**"
	find locale -name "*.po" -exec msgattrib --no-fuzzy {} -o {} \;
	msgen locale/en_GB/LC_MESSAGES/django.po -o locale/en_GB/LC_MESSAGES/django.po
	msgen locale/en_GB/LC_MESSAGES/djangojs.po -o locale/en_GB/LC_MESSAGES/djangojs.po

.PHONY: mo
mo:
	$(VIRTUAL_ENV)/bin/python manage.py compilemessages
