IMAGE_NAME ?= simple-copilot:local
INSTALL_DIR ?= $(HOME)/.local/bin
LAUNCHER ?= $(INSTALL_DIR)/simple-copilot
BUILDX_CMD := $(shell if docker buildx version >/dev/null 2>&1; then printf '%s' 'docker buildx'; elif command -v docker-buildx >/dev/null 2>&1; then printf '%s' 'docker-buildx'; fi)

.PHONY: build build-buildkit run install install-bin

build:
	@if [ -n "$(BUILDX_CMD)" ]; then \
	  $(BUILDX_CMD) build --load -t $(IMAGE_NAME) .; \
	else \
	  echo "docker buildx not found; falling back to docker build." >&2; \
	  docker build -t $(IMAGE_NAME) .; \
	fi

build-buildkit:
	@if [ -n "$(BUILDX_CMD)" ]; then \
	  $(BUILDX_CMD) build --load -t $(IMAGE_NAME) .; \
	else \
	  echo "docker buildx not found. Install docker-buildx or a Docker CLI buildx plugin." >&2; \
	  exit 1; \
	fi

run:
	docker run --rm -it \
	  -v "$$(pwd):/workspace" \
	  -v "$$HOME/.config/github-copilot:/root/.config/github-copilot:ro" \
	  -v "$$HOME/.config/gh:/root/.config/gh:ro" \
	  -e GH_TOKEN="$${GH_TOKEN:-$$(gh auth token)}" \
	  $(IMAGE_NAME)

install: build install-bin

install-bin:
	mkdir -p "$(INSTALL_DIR)"
	printf '%s\n' \
	  '#!/usr/bin/env bash' \
	  'set -euo pipefail' \
	  'exec docker run --rm -it \' \
	  '  -v "$$PWD:/workspace" \' \
	  '  -v "$$HOME/.config/github-copilot:/root/.config/github-copilot:ro" \' \
	  '  -v "$$HOME/.config/gh:/root/.config/gh:ro" \' \
	  '  -e GH_TOKEN="$${GH_TOKEN:-$$(gh auth token)}" \' \
	  '  $(IMAGE_NAME) "$$@"' \
	  > "$(LAUNCHER)"
	chmod +x "$(LAUNCHER)"
	@echo "Installed $(LAUNCHER)"
