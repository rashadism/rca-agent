.PHONY: install dev lint format check test clean build k3d.build

TAG ?= latest
IMAGE_NAME = ghcr.io/openchoreo/observer-ai-rca
K3D_CLUSTER = openchoreo

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

k3d.build: build
	k3d image import $(IMAGE_NAME):$(TAG) -c $(K3D_CLUSTER)

install:
	uv sync

dev:
	uv run uvicorn src.main:app --reload

start:
	uv run uvicorn src.main:app

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check . && uv run ruff format --check .

fix:
	uv run ruff check --fix . && uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "logs" -exec rm -rf {} +
