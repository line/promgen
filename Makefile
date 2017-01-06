.PHONY build:
build:
	docker-compose build

up:
	docker-compose up

down:
	docker-compose down

.PHONY shell:
shell:
	docker-compose run base bash

.PHONY test:
test:
	docker-compose run base promgen test
