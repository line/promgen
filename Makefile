.PHONY: build up down shell test worker web docs
up:
	docker-compose up

build:
	docker-compose build

down:
	docker-compose down

clean: down
	docker-compose rm

shell:
	docker-compose run --rm worker bash

test:
	docker-compose run base promgen test

docs:
	.venv/bin/sphinx-build -avb html docs dist/html
