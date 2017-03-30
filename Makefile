.PHONY: build up down shell test worker web
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
	docker-compose run --rm worker test

worker:
	docker-compose run --rm worker

web:
	docker-compose run --rm web
