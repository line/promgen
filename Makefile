test:
	pipenv run promgen test
.PHONY: test
 
build:
	docker-compose build
.PHONY: build

shell:
	docker-compose run --rm worker bash
.PHONY:	shell

docs:
	pipenv run sphinx-build -avb html docs dist/html
.PHONY: docs

clean:
	rm -rf .venv dist
.PHONY:	clean
