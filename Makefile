.PHONY: test
test: .venv
	.venv/bin/promgen test

.PHONY: build 
build:
	docker-compose build

.PHONY:	shell
shell:
	docker-compose run --rm worker bash

.venv:
	python3 -m venv .venv
	.venv/bin/pip install -e .[dev,docs,mysql]

.PHONY: docs
docs: .venv
	.venv/bin/sphinx-build -avb html docs dist/html

.PHONY:	clean
clean:
	rm -rf .venv dist
