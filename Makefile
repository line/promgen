lessopts="--tabs=4 --quit-if-one-screen --RAW-CONTROL-CHARS --no-init"

ENV_DIR := .venv
PIP_BIN := $(ENV_DIR)/bin/pip
PIP_COMPILE := $(ENV_DIR)/bin/pip-compile

APP_BIN := $(ENV_DIR)/bin/promgen
CELERY_BIN := $(ENV_DIR)/bin/celery
SPHINX  := $(ENV_DIR)/bin/sphinx-build
RUFF_BIN := $(ENV_DIR)/bin/ruff
BLACK_BIN := $(ENV_DIR)/bin/black

DOCKER_TAG := promgen:local
SYSTEM_PYTHON ?= python3.9

# Help 'function' taken from
# https://gist.github.com/prwhite/8168133#gistcomment-2278355

# COLORS
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

TARGET_MAX_CHAR_NUM=20
.PHONY:	help
## Show help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  $(YELLOW)make$(RESET) $(GREEN)<target>$(RESET)'
	@echo ''
	@echo 'Targets:'
	@awk '/^[\%a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  $(YELLOW)%-$(TARGET_MAX_CHAR_NUM)s$(RESET) $(GREEN)%s$(RESET)\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

###############################################################################
### Pip Tasks
###############################################################################

$(APP_BIN): $(PIP_BIN)
	$(PIP_BIN) install -e .[dev,mysql] -r docker/requirements.txt

$(PIP_BIN):
	$(SYSTEM_PYTHON) -m venv $(ENV_DIR)
	$(PIP_BIN) install --upgrade pip wheel

.PHONY: list
list: $(PIP_BIN)
	$(PIP_BIN) list --outdated

$(PIP_COMPILE): $(PIP_BIN)
	$(PIP_BIN) install pip-tools

docker/requirements.txt: $(PIP_COMPILE) setup.py setup.cfg docker/requirements.in
	$(PIP_COMPILE) --output-file docker/requirements.txt setup.py docker/requirements.in --no-emit-index-url

.PHONY: pip
## Reinstall with pip
pip: docker/requirements.txt
	$(PIP_BIN) install --upgrade pip wheel
	$(PIP_BIN) install -e .[dev,mysql] -r docker/requirements.txt

.PHONY: compile
## Pip: Compile requirements
compile: docker/requirements.txt

###############################################################################
### Other Tasks
###############################################################################

.PHONY: build
## Docker: Build container
build:
	docker build . --tag $(DOCKER_TAG)

.PHONY: demo
## Docker: Run a demo via docker-compose
demo:
	docker-compose up

#### Django Commands

.PHONY: test
test: $(APP_BIN)
## Django: Run tests
	$(APP_BIN) collectstatic --noinput
	$(APP_BIN) test -v 2 --buffer

.PHONY: bootstrap
## Django: Bootstrap install
bootstrap: $(APP_BIN)
	$(APP_BIN) bootstrap
	$(APP_BIN) migrate
	$(APP_BIN) check

.PHONY: check
## Django: Run Django checks
check: $(APP_BIN)
	$(APP_BIN) check

.PHONY: migrate
## Django: Run migrations
migrate: $(APP_BIN)
	$(APP_BIN) migrate

.PHONY:	run
## Django: Run development server
run: migrate primevue
	$(APP_BIN) runserver

.PHONY: shell
## Django: Development shell
shell: $(APP_BIN)
	@echo opening promgen shell
	@$(APP_BIN) shell

dump: $(APP_BIN)
	$(APP_BIN) dumpdata promgen.DefaultExporter  --indent=2 --output promgen/fixtures/exporters.yaml --format=yaml
.PHONY: load
load: $(APP_BIN)
	$(APP_BIN) loaddata exporters

#### Documentation

$(SPHINX): $(PIP_BIN)
	$(PIP_BIN) install -e .[dev,docs]

.PHONY: docs
## Sphinx: Build documentation
docs: $(SPHINX)
	$(SPHINX) -avb html docs dist/html

$(RUFF_BIN): $(PIP_BIN)
	$(PIP_BIN) install ruff

$(BLACK_BIN): $(PIP_BIN)
	$(PIP_BIN) install black

.PHONY: format
format: $(RUFF_BIN) $(BLACK_BIN)
	$(RUFF_BIN) check promgen --fix
	$(BLACK_BIN) promgen


#### Other assorted commands

.PHONY: clean
## Clean our repo
clean:
	@echo Removing venv
	@rm -rf .venv
	@echo Clearing dist files
	@rm -rf dist

.PHONY: changelog
changelog:
	git log --color=always --first-parent --pretty='format:%s|%Cgreen%d%Creset' | column -ts '|' | less "$(lessopts)"

.PHONY: primevue
primevue: primevue-gen/node_modules promgen/static/primevue/main.css promgen/static/primevue/main.js

primevue-gen/node_modules: primevue-gen/package.json
	cd primevue-gen && npm i --no-package-lock

promgen/static/primevue/main.css promgen/static/primevue/main.js: primevue-gen/build.js primevue-gen/src/main.js
	cd primevue-gen && npm run build
