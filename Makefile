VIRTUAL_ENV ?= venv
NODE_BIN = node_modules/.bin
SOURCE_DIRS = wine_cellar tests
ARGUMENTS=$(filter-out $(firstword $(MAKECMDGOALS)), $(MAKECMDGOALS))

.PHONY: all
all: help

.PHONY: install
install:
	npm install --no-save
	if [ ! -f $(VIRTUAL_ENV)/bin/python3 ]; then python3 -m venv $(VIRTUAL_ENV); fi
	$(VIRTUAL_ENV)/bin/python3 -m pip install --upgrade -r requirements.txt
	$(VIRTUAL_ENV)/bin/python3 manage.py migrate

.PHONY: clean
clean:
	if [ -f package-lock.json ]; then rm package-lock.json; fi
	if [ -d node_modules ]; then rm -rf node_modules; fi
	if [ -d venv ]; then rm -rf venv; fi

.PHONY: server
server:
	$(VIRTUAL_ENV)/bin/python3 manage.py runserver 8003

.PHONY: watch
watch:
	trap 'kill %1' KILL; \
	$(VIRTUAL_ENV)/bin/python3 manage.py runserver 8003

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

.PHONY: lint-html-files
lint-html:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/djlint $(ARGUMENTS) --profile=django --ignore=H030,H031,T002 || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: lint-py
lint-python-files:
	EXIT_STATUS=0; \
	$(VIRTUAL_ENV)/bin/black $(ARGUMENTS) || EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/isort $(ARGUMENTS) --filter-files || EXIT_STATUS=$$?; \
	$(VIRTUAL_ENV)/bin/flake8 $(ARGUMENTS) || EXIT_STATUS=$$?; \
	exit $${EXIT_STATUS}

.PHONY: po
po:
	$(VIRTUAL_ENV)/bin/python manage.py makemessages --all -d django --extension html,email,py
	$(VIRTUAL_ENV)/bin/python manage.py makemessages --all -d djangojs --ignore '$(VIRTUAL_ENV)/*'
	msgen locale/en_GB/LC_MESSAGES/django.po -o locale/en_GB/LC_MESSAGES/django.po
	msgen locale/en_GB/LC_MESSAGES/djangojs.po -o locale/en_GB/LC_MESSAGES/djangojs.po

.PHONY: mo
mo:
	$(VIRTUAL_ENV)/bin/python manage.py compilemessages
