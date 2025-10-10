# RPA Database (rpa_db)

This folder contains Alembic migrations and configuration for a separate Postgres database named `rpa_db`, independent from Airflow's metadata DB.

## Environment Variables

Create a `.env` file in this `src/database/` directory (or export these in your shell) using `.env.example` as a template:

- `RPA_DB_HOST` (default: `postgres` when running via docker-compose)
- `RPA_DB_PORT` (default: `5432`)
- `RPA_DB_USER`
- `RPA_DB_PASSWORD`
- `RPA_DB_NAME` (default: `rpa_db`)

Example (`src/database/.env`):

```
RPA_DB_HOST=postgres
RPA_DB_PORT=5432
RPA_DB_USER=airflow
RPA_DB_PASSWORD=airflow
RPA_DB_NAME=rpa_db
```

## Creating the rpa_db database

We reuse the existing `postgres` service from `docker-compose.yml`. To create `rpa_db` without touching Airflow's DB, run a one-off command:

```powershell
# Create rpa_db if it does not exist (idempotent)
docker compose exec -T postgres psql -U ${env:POSTGRES_USER} -d ${env:POSTGRES_DB} -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rpa_db') THEN PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE rpa_db'); END IF; END $$;" 2>$null
```

If `dblink` is not available, you can simply run:

```powershell
docker compose exec -T postgres psql -U ${env:POSTGRES_USER} -d ${env:POSTGRES_DB} -c "CREATE DATABASE rpa_db" 2>$null
```

Run either command once. This does not change Airflow's DB.

## Alembic Setup

Install Alembic in your Python environment (outside containers is fine):

```powershell
pip install alembic psycopg2-binary python-dotenv
```

## Running Migrations

From the repository root (Makefile provided):

```powershell
# Upgrade to latest
make db-upgrade

# Downgrade one revision
make db-downgrade

# Create a new autogenerate revision with a label
make db-rev LABEL="add-new-table"
```

Directly via Alembic (inside `src/database/`):

```powershell
cd database
alembic upgrade head
alembic downgrade -1
alembic revision -m "add-new-table" --autogenerate
```

Alembic builds the `sqlalchemy.url` from the `RPA_DB_*` environment variables.

## Verifying Schema

After `alembic upgrade head`, verify tables, indexes, and FKs:

```powershell
# psql into rpa_db
docker compose exec -T postgres psql -U ${env:POSTGRES_USER} -d rpa_db -c "\dt+"

# Check indexes
docker compose exec -T postgres psql -U ${env:POSTGRES_USER} -d rpa_db -c "\di+"

# Check foreign keys
docker compose exec -T postgres psql -U ${env:POSTGRES_USER} -d rpa_db -c "SELECT conname, contype, confdeltype, conrelid::regclass AS table_name FROM pg_constraint WHERE contype='f';"
```

Expected objects:
- Tables: `rpa_definitions`, `rpa_automation_exec`, `rpa_steps_exec`
- Unique constraint on `rpa_steps_exec (exec_id, event_number)`
- ON DELETE CASCADE from `rpa_automation_exec.exec_id` to `rpa_steps_exec.exec_id`
- Indexes per README spec

## Notes

- This `src/database/` folder is isolated from Airflow configs.
- No triggers are used; application code should manage `updated_at` on update.
