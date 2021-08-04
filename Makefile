lessopts="--tabs=4 --quit-if-one-screen --RAW-CONTROL-CHARS --no-init"

APP_BIN := .venv/bin/promgen
PIP_BIN := .venv/bin/pip
SPHINX  := .venv/bin/sphinx-build
DOCKER_TAG := promgen:local

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
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[\%a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

${PIP_BIN}:
	python3 -m venv .venv
	${PIP_BIN} install -U pip setuptools

${APP_BIN}: ${PIP_BIN}
	${PIP_BIN} install -e .[dev,mysql] -r docker/requirements.txt

.PHONY: pip
pip: ${PIP_BIN}
	${PIP_BIN} install -e .[dev,mysql] -r docker/requirements.txt

.PHONY: build
## Docker: Build container
build:
	docker build . --tag ${DOCKER_TAG}

.PHONY: demo
## Docker: Run a demo via docker-compose
demo:
	docker-compose up

#### Django Commands

.PHONY: test
test: ${APP_BIN}
## Django: Run tests
	${APP_BIN} collectstatic --noinput
	${APP_BIN} test -v 2

.PHONY: bootstrap
## Django: Bootstrap install
bootstrap: ${APP_BIN}
	${APP_BIN} bootstrap
	${APP_BIN} migrate
	${APP_BIN} check

.PHONY: check
## Django: Run Django checks
check: ${APP_BIN}
	${APP_BIN} check

.PHONY: migrate
## Django: Run migrations
migrate: ${APP_BIN}
	${APP_BIN} migrate

.PHONY:	run
## Django: Run development server
run: migrate
	${APP_BIN} runserver

.PHONY: shell
## Django: Development shell
shell: ${APP_BIN}
	@echo opening promgen shell
	@${APP_BIN} shell

dump: ${APP_BIN}
	${APP_BIN} dumpdata promgen.DefaultExporter  --indent=2 --output promgen/fixtures/exporters.yaml --format=yaml
.PHONY: load
load: ${APP_BIN}
	${APP_BIN} loaddata exporters

#### Documentation

${SPHINX}: ${PIP_BIN}
	${PIP_BIN} install -e .[dev,docs]

.PHONY: docs
## Sphinx: Build documentation
docs: ${SPHINX}
	${SPHINX} -avb html docs dist/html


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
