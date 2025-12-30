UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: build inspect process

build:
	UID=$(UID) GID=$(GID) docker compose build

inspect:
	UID=$(UID) GID=$(GID) docker compose run --rm audiomason inspect $(P)

process:
	UID=$(UID) GID=$(GID) docker compose run --rm audiomason process $(P)
