# Repository Guidelines

## Project Structure & Module Organization
- `airflow/` – Airflow image, DAGs (`airflow/src/dags`), and helpers (`airflow/src/services`, `airflow/src/api`).
- `rpa-api/` – FastAPI service (CQRS/Saga orchestration) under `rpa-api/src`.
- `rpa-listener/` – RabbitMQ listener that triggers robots (`rpa-listener/src`).
- `rpa-robots/` – Robot Framework tests (`rpa-robots/tests`, outputs in `rpa-robots/results`).
- `src/database` – Alembic config and migrations; `src/config` – Postgres/RabbitMQ; `shared/data` – sample assets.
- Top-level: `docker-compose.yml`, `Makefile`, `.env`, `documentation/`.

## Build, Test, and Development Commands
- Start full stack: `docker compose up -d`
- Airflow UI: http://localhost:8080 (created by `airflow-init` service)
- Database migrations: `make db-upgrade` | new rev: `make db-rev LABEL=add-x`
- Run API locally: `cd rpa-api && uvicorn src.main:app --reload --port 3000`
- Run listener locally: `cd rpa-listener && python main.py`
- Run robots: `cd rpa-robots && robot -d results tests/`

## Coding Style & Naming Conventions
- Python 3.11, 4-space indent, 120-char lines.
- Use `pre-commit` in `rpa-api` (black, isort, autoflake, pylint): `pre-commit run -a`.
- Naming: modules `snake_case.py`, classes `CamelCase`, functions/vars `snake_case`.
- Airflow DAGs: `airflow/src/dags/dag_<name>.py`; tasks in `airflow/src/dags/tasks/`.
- Robot tests: `tests/<feature>_test.robot` or `<feature>.robot`.

## Testing Guidelines
- Robot Framework: prefer E2E flows in `rpa-robots/tests`; store outputs in `rpa-robots/results`.
- API/Listener: add unit tests near modules (pytest recommended; none enforced yet).
- Airflow: validate DAG import locally and trigger in UI; keep idempotent tasks.

## Commit & Pull Request Guidelines
- Commit style (history is mixed): prefer Conventional Commits, e.g. `feat(api): add saga endpoint`.
- Keep subject ≤72 chars; meaningful body when needed.
- PRs must include: clear description, linked issues, test steps, relevant logs/screenshots, and affected services (airflow/api/listener/robots).

## Security & Configuration Tips
- Do not commit secrets; use `.env` and Azure Key Vault/AWS Secrets Manager.
- Use provided scripts under `src/scripts/` (e.g., `load-aws-secrets.ps1`, `verify-secrets.ps1`).
- Review envs in `docker-compose.yml` before running; rotate keys if leaked.

## Agent-Specific Notes
- Keep changes minimal and service-scoped; follow existing folder boundaries.
- Prefer `Makefile` and compose tasks over ad-hoc scripts; update docs when adding commands.

