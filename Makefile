PYTHON ?= python3

.PHONY: help train up down test lint clean

help:
	@echo "Available make targets:"
	@echo "  make train [SUBSET=50]  - Train student model on teacher labels"
	@echo "  make up                 - Build and deploy full cluster environment"
	@echo "  make down               - Delete and teardown local cluster"
	@echo "  make test               - Run all test suites"
	@echo "  make lint               - Run code linter"

train:
	$(PYTHON) training/train.py $(if $(SUBSET),--subset $(SUBSET),)

up:
	k3d cluster create --config cluster/k3d.yaml || true
	kubectl apply -f cluster/seaweedfs.yaml
	kubectl apply -f cluster/app.yaml

down:
	k3d cluster delete mini-cloud || true

test:
	pytest tests/

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

