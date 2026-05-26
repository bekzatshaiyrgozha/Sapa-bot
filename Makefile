PYTHON ?= python3
VENV = .venv311

.PHONY: venv install bootstrap start-db stop-db logs run docker-run test

venv:
	@echo "Creating virtualenv $(VENV) (uses pyenv-selected python if available)..."
	$(PYTHON) -m venv $(VENV) || (echo "venv creation failed, try using virtualenv or pyenv"; exit 1)

bootstrap: venv
	@echo "Bootstrapping venv: installing pip/setuptools/wheel and requirements"
	. $(VENV)/bin/activate && python -m ensurepip --upgrade || true
	. $(VENV)/bin/activate && python -m pip install --upgrade pip setuptools wheel
	. $(VENV)/bin/activate && pip install -r requirements.txt

install: bootstrap

start-db:
	docker-compose up -d db

stop-db:
	docker-compose stop db || true

logs:
	docker-compose logs -f

run:
	@echo "Run bot locally (ensure .env is set and venv activated)"
	set -a; source .env; set +a; . $(VENV)/bin/activate; python -m bot.main

docker-run:
	docker-compose up --build --remove-orphans

test:
	. $(VENV)/bin/activate && pytest -q
