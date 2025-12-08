SHELL := /bin/sh

.PHONY: db-upgrade db-downgrade db-rev

DB_DIR := src/database

# Upgrade to latest head
db-upgrade:
	cd $(DB_DIR) && alembic upgrade head

# Downgrade one revision
db-downgrade:
	cd $(DB_DIR) && alembic downgrade -1

# Create a new revision with label
# Usage: make db-rev LABEL="add-feature-x"
db-rev:
	@if [ -z "$(LABEL)" ]; then echo "LABEL is required, e.g. make db-rev LABEL=add-x"; exit 1; fi
	cd $(DB_DIR) && alembic revision -m "$(LABEL)" --autogenerate
