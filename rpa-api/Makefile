# RPA API Makefile

.PHONY: help test test-unit test-integration test-coverage test-html clean install-test

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-test: ## Install test dependencies
	pip install -r requirements-test.txt

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest -m unit

test-integration: ## Run integration tests only
	pytest -m integration

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=term-missing --cov-report=html:htmlcov

test-html: ## Generate HTML test report
	pytest --html=reports/test-report.html --self-contained-html

test-parallel: ## Run tests in parallel
	pytest -n auto

test-verbose: ## Run tests with verbose output
	pytest -v -s

test-specific: ## Run specific test file (usage: make test-specific FILE=test_file.py)
	pytest tests/$(FILE)

clean: ## Clean test artifacts
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf reports/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

coverage-report: ## Generate detailed coverage report
	coverage run -m pytest
	coverage report
	coverage html
	@echo "Coverage report generated in htmlcov/index.html"

coverage-badge: ## Generate coverage badge
	coverage run -m pytest
	coverage-badge -o coverage.svg

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw --runner "pytest -xvs"

lint-test: ## Run linting on test files
	flake8 tests/
	black --check tests/
	isort --check-only tests/

format-test: ## Format test files
	black tests/
	isort tests/
