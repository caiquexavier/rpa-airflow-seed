SHELL := /bin/sh

.PHONY: db-upgrade db-downgrade db-reset db-rev test test-unit test-cov test-html install-test-deps

DB_DIR := src/database
TEST_DIR := tests

# Upgrade to latest head
db-upgrade:
	cd $(DB_DIR) && alembic upgrade head

# Downgrade one revision
db-downgrade:
	cd $(DB_DIR) && alembic downgrade -1

# Reset database: downgrade to base then upgrade to head
db-reset:
	cd $(DB_DIR) && alembic downgrade base && alembic upgrade head

# Create a new revision with label
# Usage: make db-rev LABEL="add-feature-x"
db-rev:
	@if [ -z "$(LABEL)" ]; then echo "LABEL is required, e.g. make db-rev LABEL=add-x"; exit 1; fi
	cd $(DB_DIR) && alembic revision -m "$(LABEL)" --autogenerate

# Install test dependencies
install-test-deps:
	pip install -r $(TEST_DIR)/requirements.txt

# Run all tests
test:
	PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src pytest $(TEST_DIR) -v

# Run unit tests only
test-unit:
	PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src pytest $(TEST_DIR) -v -m unit

# Run tests with coverage report
test-cov:
	PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src pytest $(TEST_DIR) --cov --cov-report=term-missing

# Generate HTML coverage report
test-html:
	PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src pytest $(TEST_DIR) --cov --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"
