lessopts="--tabs=4 --quit-if-one-screen --RAW-CONTROL-CHARS --no-init"

APP_BIN := .venv/bin/promgen
PIP_BIN := .venv/bin/pip
SPHINX  := .venv/bin/sphinx-build

.PHONY: test
test: ${APP_BIN}
	${APP_BIN} test -v 2

${PIP_BIN}:
	python3 -m venv .venv
	${PIP_BIN} pip -U pip

${APP_BIN}: ${PIP_BIN}
	${PIP_BIN} install -r docker/requirements.txt
	${PIP_BIN} install -e .[dev,mysql]

.PHONY: build
## Build docker container
build:
	docker-compose build base

.PHONY: migrate
## Run Django migrations
migrate: ${APP_BIN}
	${APP_BIN} migrate

.PHONY:	run
## Run Django server
run: migrate
	${APP_BIN} runserver

.PHONY: shell
## Django development shell
shell: ${APP_BIN}
	@echo opening promgen shell
	@${APP_BIN} shell

.PHONY: docs
## Build sphinx docs
docs:
	${SPHINX} -avb html docs dist/html

.PHONY: clean
clean:
	@echo Removing venv
	@rm -rf .venv
	@echo Clearing dist files
	@rm -rf dist

dump: ${APP_BIN}
	${APP_BIN} dumpdata promgen.DefaultExporter  --indent=2 --output promgen/fixtures/exporters.yaml --format=yaml
.PHONY: load
load: ${APP_BIN}
	${APP_BIN} loaddata exporters

.PHONY: circleci
## Test circleci configuration locally
circleci:
	circleci local execute

.PHONY: changelog
changelog:
	git log --color=always --first-parent --pretty='format:%s|%Cgreen%d%Creset' | column -ts '|' | less "$(lessopts)" 
