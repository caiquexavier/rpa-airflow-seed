# Apache Airflow + Postgres (Docker Compose)

Minimal Airflow 2.9.3 + Postgres 15 using LocalExecutor.

## Quickstart
1. Initialize DB and create admin user
   `ash
   docker compose up airflow-init
   `
2. Start services
   `ash
   docker compose up -d
   `
3. Open UI: http://localhost:8080 (use creds from .env)

## Files
- .env  all credentials and configs
- docker-compose.yml  services, healthchecks, named volume
- irflow/dags/  DAGs (contains example_dag.py)
- irflow/logs/  persistent logs

## Notes
- Ensure .env is UTF-8 without BOM or ASCII. Only KEY=value lines.
- Change default Postgres and Airflow credentials before production.
