
format:
	poetry run black $(DIRS)
	poetry run isort $(DIRS)
.PHONY: format

build:
	docker build -t keycloak-iat-vault .
.PHONY: build
