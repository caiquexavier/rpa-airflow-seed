## RPA Airflow Seed — Full Stack Overview

This repository is a minimal, production-ready seed for orchestrating RPA workloads with Apache Airflow and executing browser automations with Robot Framework.

### Stack
- Airflow 2.9.3 (LocalExecutor) with custom image build in `airflow/Dockerfile`.
- Postgres 15 as Airflow metadata database.
- Docker Compose for orchestration of services.
- Robot Framework project in `rpa-robots/` using `robotframework`, `robotframework-browser` (Playwright), and `rpaframework` on Python 3.11.
- PowerShell 7 support for Windows automation.

### Prerequisites (Windows)
- Git, Docker Desktop
- Python 3.11
- PowerShell 7 (pwsh)
- Google Chrome or Microsoft Edge
- Visual C++ Redistributable 2015–2022

### Quick Start
1) Robot Framework environment
```powershell
cd rpa-robots
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
rfbrowser init
```

2) Airflow + Postgres
```powershell
cd ..
docker compose up airflow-init
docker compose up -d
```
Open Airflow UI: http://localhost:8080

### Project Structure
```
rpa/
  airflow/
    Dockerfile           # Airflow image (provider pinning)
    dags/                # DAGs (e.g., example)
    logs/                # Persisted Airflow logs (gitignored)
  rpa-robots/
    tests/               # Robot tests
    resources/           # Shared keywords/resources
    variables/           # Python/Robot variables
    results/             # Robot output (gitignored)
    requirements.txt     # Robot dependencies
  docker-compose.yml     # Airflow + Postgres services
  .env                   # Credentials and config (not committed)
```

### Common Commands
- Run Robot tests locally
```powershell
cd rpa-robots
venv\Scripts\activate
robot -d results tests
```

- Inspect Airflow logs
```
airflow/logs/  (on host)
```

- Rebuild Airflow image (if you change `airflow/Dockerfile`)
```powershell
docker compose build
docker compose up -d
```

### Notes
- Keep `.env` simple `KEY=VALUE` without quotes; prefer UTF-8 (no BOM).
- Change default credentials before any non-local usage.
