lessopts="--tabs=4 --quit-if-one-screen --RAW-CONTROL-CHARS --no-init"

.PHONY: test
test: pipenv
	pipenv run promgen test

.PHONY:	all
all: clean pipenv test build


.PHONY: build
build:
	docker-compose build base


.PHONY:	shell
shell:
	docker-compose run --rm worker bash


.PHONY: docs
docs:
	pipenv run sphinx-build -avb html docs dist/html


.PHONY:	pipenv
pipenv:
	@echo Testing if Pipenv is already installed
	@pipenv --venv 1> /dev/null 2> /dev/null || pipenv install --dev


.PHONY:	clean
clean:
	@echo Removing Pipenv
	@pipenv --rm || true
	@echo Clearing dist files
	@rm -rf dist


.PHONY:	dump
dump: pipenv
	pipenv run promgen dumpdata promgen.DefaultExporter  --indent=2 --output promgen/fixtures/exporters.yaml --format=yaml

.PHONY:	load
load: pipenv
	pipenv run promgen loaddata exporters

.PHONY: circleci
circleci:
	circleci local execute

.PHONY: changelog
changelog:
	git log --color=always --first-parent --pretty='format:%s|%Cgreen%d%Creset' | column -ts '|' | less "$(lessopts)"
