# RPA Airflow Seed — Complete RPA Orchestration Platform

A production-ready platform for orchestrating RPA workloads with Apache Airflow, featuring a complete message queue system and browser automation capabilities.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Airflow UI    │    │   RPA API       │    │  RPA Listener   │
│  (Orchestrator) │───▶│  (FastAPI)      │───▶│  (Worker)       │
│  localhost:8080 │    │  localhost:3000 │    │  (PowerShell)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   RabbitMQ      │    │  Robot Framework│
         │              │  (Message Queue)│    │  (Automation)   │
         │              │ localhost:15672 │    │  (Browser Tests)│
         │              └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  (Airflow DB)   │
│ localhost:5432  │
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** VM
- **Python 3.11.x** (`python --version`)
- **Node.js 20.x LTS** via **NVM for Windows**
- **Docker Desktop** (for Airflow and RPA API services)
- **Google Chrome or Microsoft Edge** (for browser automation)

### 1) Install NVM for Windows
```powershell
# Option A: Using winget
winget install CoreyButler.NVMforWindows

# Option B: Download from https://github.com/coreybutler/nvm-windows/releases
# Install nvm-setup.exe as Administrator
```

### 2) Install Node.js LTS
```powershell
# Install and use Node.js 20 LTS
nvm install 20
nvm use 20

# Verify installation
node -v
npm -v
```

### 3) AWS Secrets Manager Setup

#### Prerequisites
- **AWS CLI** must be installed and configured
- AWS credentials configured via `aws configure` or environment variables
- Permission to access the secret `dev/rpa-airflow` in region `eu-north-1`

#### Install AWS CLI (if not already installed)
```powershell
# Download and install AWS CLI from https://aws.amazon.com/cli/
# Or use winget:
winget install Amazon.AWSCLI

# Verify installation
aws --version
```

#### Configure AWS Credentials
```powershell
# Configure AWS credentials
aws configure

# Or set environment variables:
$env:AWS_ACCESS_KEY_ID = "your-access-key"
$env:AWS_SECRET_ACCESS_KEY = "your-secret-key"
$env:AWS_DEFAULT_REGION = "eu-north-1"
```

#### Load Secrets from AWS Secrets Manager
```powershell
# Load secrets from AWS Secrets Manager and export to environment
. .\src\scripts\load-aws-secrets.ps1

# Verify secrets are loaded (optional)
aws secretsmanager get-secret-value --secret-id dev/rpa-airflow --region eu-north-1
```

**Note:** The `load-aws-secrets.ps1` script must be run before starting Docker Compose. It fetches all environment variables from AWS Secrets Manager secret `dev/rpa-airflow` and exports them to the current PowerShell session.

#### Local Development (Optional)
For local testing, you can still use `.env` files (excluded from production). However, the bootstrap script will override any local `.env` values when run in production mode.

### 4) Environment Setup (Legacy - Optional for Local Development)
```powershell
# Run the setup script to configure environment and install dependencies (local development only)
powershell -ExecutionPolicy Bypass -File src/scripts/setup-env.ps1
```

**Note:** This script is for local development only. In production, use AWS Secrets Manager as described above.

### 5) Start Services

#### Start Docker Services (Airflow, RPA API, RabbitMQ, PostgreSQL)
```powershell
# Start all Docker services
npm run up

# Check status
npm run status

# View logs
npm run logs
```

#### Start RPA Listener (PowerShell)
```powershell
# Start the RPA Listener in a separate PowerShell window
npm run start:listener
```

### 6) Configure Airflow Variables and Connections

**Note:** The following Airflow configuration is automatically set during container initialization:

- **Variable:** `ECARGO_XLSX_PATH` = `/opt/airflow/data/Controle_Unilever_Personalizado.xlsx`
- **Connection:** `rpa_api` = `http://rpa-api:3000`

These are configured automatically by the `airflow-init` service, so no manual configuration is required.

If you need to modify these values, you can:
- Update them in the Airflow UI (Admin > Variables / Connections)
- Or modify the `airflow-init` service configuration in `docker-compose.yml`

### 7) Access Services
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **RPA API**: http://localhost:3000
- **RabbitMQ Management**: http://localhost:15672 (credentials from Key Vault)
- **API Health Check**: http://localhost:3000/health

### 8) Development Mode (Optional)
```powershell
# For development, you can run services individually:

# RPA API (if not using Docker)
cd rpa-api
venv\Scripts\activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 3000

# RPA Listener
cd rpa-listener
venv\Scripts\activate
python main.py

# Robot Tests
cd rpa-robots
venv\Scripts\activate
rfbrowser init
robot -d results tests/
```

## 📁 Project Structure

```
rpa-airflow-seed/
├── package.json              # Helper scripts for Docker and PowerShell
├── docker-compose.yml        # Docker orchestration
├── .env                      # Environment variables (secrets)
├── src/                      # Source code and configuration
│   ├── scripts/              # PowerShell setup and management scripts
│   │   ├── setup-env.ps1     # Environment setup and dependency installation
│   │   └── start-listener.ps1 # PowerShell script to start RPA Listener
│   ├── config/               # Configuration files
│   │   └── rabbitmq/
│   │       └── definitions.json # RabbitMQ queue definitions
│   ├── data/                 # Data files
│   └── database/             # Database migrations
├── airflow/                   # Airflow orchestration
│   ├── Dockerfile             # Custom Airflow image
│   ├── dags/                  # Workflow definitions
│   │   └── dag_ecargo_pod_download.py
│   ├── libs/                  # Shared utilities
│   │   └── converter.py       # Excel to RPA request converter
│   ├── data/                  # Data files
│   │   └── Controle_Unilever_Personalizado.xlsx
│   └── logs/                  # Airflow logs
├── rpa-api/                   # FastAPI service
│   ├── Dockerfile             # Docker image for RPA API
│   ├── src/
│   │   ├── controllers/       # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── libs/             # RabbitMQ client
│   │   └── validations/      # Request validation
│   └── requirements.txt
├── rpa-listener/              # Message queue worker (PowerShell)
│   ├── main.py               # RabbitMQ listener
│   └── requirements.txt
├── rpa-robots/               # Robot Framework tests
│   ├── tests/                # Test suites
│   ├── resources/            # Reusable keywords
│   └── results/              # Test outputs
```

## 🔧 Features

### Airflow Orchestration
- **Custom Docker Image**: Pinned Apache Airflow 2.9.3 with Microsoft WinRM provider
- **LocalExecutor**: Single-node execution for development
- **PostgreSQL Backend**: Persistent metadata storage
- **DAG Management**: Visual workflow management at http://localhost:8080

### RPA API (FastAPI) - Docker Container
- **RESTful Endpoints**: `/request_rpa_exec`, `/health`
- **RabbitMQ Integration**: Message queue publishing
- **Pydantic Validation**: Type-safe request handling
- **MVC Architecture**: Clean separation of concerns
- **Docker Containerized**: Runs on port 3000
- **Health Checks**: Built-in health monitoring

### RPA Listener (Worker) - PowerShell
- **RabbitMQ Consumer**: Processes queued RPA jobs
- **PowerShell Integration**: Executes Robot Framework tests
- **Error Handling**: Graceful failure management
- **Auto-reconnection**: Resilient message processing
- **Environment Loading**: Automatic `.env` file loading
- **Standalone Process**: Runs independently in PowerShell

### Robot Framework Automation
- **Browser Testing**: Playwright-based automation
- **RPA Framework**: Enterprise RPA capabilities
- **Test Organization**: Modular test structure
- **Results Management**: HTML reports and logs

### Message Queue System
- **RabbitMQ**: Reliable message delivery
- **Queue Management**: Web UI at http://localhost:15672
- **Message Routing**: Flexible job distribution
- **Durability**: Persistent message storage

### Docker Container Management
- **Service Orchestration**: Docker Compose manages all services
- **Health Monitoring**: Built-in health checks for all services
- **Auto-Restart**: Automatic restart on failure
- **Resource Management**: Efficient container resource usage
- **Service Discovery**: Internal networking between containers

## 🛠️ Common Commands

### Docker Services Management
```powershell
# Start all Docker services (Airflow, RPA API, RabbitMQ, PostgreSQL)
npm run up

# Stop all services
npm run down

# Restart services
npm run restart

# View logs
npm run logs
npm run logs:api
npm run logs:airflow
npm run logs:scheduler

# Check status
npm run status

# Build services
npm run build
```

### RPA Listener Management
```powershell
# Start RPA Listener in PowerShell
npm run start:listener
```

### Docker Compose Management
```powershell
# Start specific services
docker-compose up -d rpa-api
docker-compose up -d airflow-webserver

# View logs for specific service
docker-compose logs -f rpa-api
docker-compose logs -f airflow-webserver

# Rebuild specific service
docker-compose build rpa-api
docker-compose build airflow-webserver airflow-scheduler airflow-init

# Scale services (if needed)
docker-compose up -d --scale rpa-api=2
```

### Testing
```powershell
# Test RPA API health endpoint
curl http://localhost:3000/health

# Test RPA API publish endpoint
curl -X POST http://localhost:3000/request_rpa_exec -H "Content-Type: application/json" -d '{"rpa-id":"test-001"}'

# Test Airflow health endpoint
curl http://localhost:8080/health

# Run Robot tests
cd rpa-robots
venv\Scripts\activate
rfbrowser init
robot -d results tests/
```

## 🔍 Monitoring & Debugging

### Docker Services Monitoring
```powershell
# View all service status
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f rpa-api
docker-compose logs -f airflow-webserver
docker-compose logs -f airflow-scheduler

# View resource usage
docker stats
```

### Service Endpoints
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **RPA API**: http://localhost:3000
- **RPA API Health**: http://localhost:3000/health
- **RabbitMQ Management**: http://localhost:15672 (credentials from Key Vault)
- **Test Results**: `rpa-robots/results/`

## 🧪 Testing Procedures

### API Test
```powershell
# Start Docker services
npm run up

# Test RPA API health endpoint
curl http://localhost:3000/health
# Expected: {"status": "ok"}

# Test RPA API publish endpoint
curl -X POST http://localhost:3000/request_rpa_exec -H "Content-Type: application/json" -d '{"rpa-id":"docker-test-001"}'
# Expected: {"rpa-id":"docker-test-001"}

# Test Airflow health endpoint
curl http://localhost:8080/health
# Expected: {"status": "healthy"}
```

### Listener Test
```powershell
# Start RPA Listener in separate PowerShell window
npm run start:listener

# Publish test message to RabbitMQ
python - << 'PY'
import os, pika, json
user = os.getenv('RABBITMQ_DEFAULT_USER', 'admin')
pwd = os.getenv('RABBITMQ_DEFAULT_PASS', 'admin')
host = os.getenv('RABBITMQ_HOST', 'localhost')
queue = os.getenv('RABBITMQ_QUEUE', 'rpa_events')
conn = pika.BlockingConnection(pika.ConnectionParameters(host, credentials=pika.PlainCredentials(user, pwd)))
ch = conn.channel(); ch.queue_declare(queue=queue, durable=True)
ch.basic_publish(exchange='', routing_key=queue, body=json.dumps({'rpa-id':'docker-test-1'}))
conn.close()
PY

# Check listener logs in the PowerShell window
# Should show message consumption
```

### Container Restart Test
```powershell
# Restart RPA API container
docker-compose restart rpa-api

# Check if service recovers
curl http://localhost:3000/health

# View container logs
docker-compose logs rpa-api
```

## 🔐 Configuration

### AWS Secrets Manager

All sensitive configuration values are stored in **AWS Secrets Manager** secret `dev/rpa-airflow` (region: `eu-north-1`).

**Secret ARN:** `arn:aws:secretsmanager:eu-north-1:275666881463:secret:dev/rpa-airflow-GQ7oUH`

#### Required Environment Variables

The following environment variables must be present in the AWS secret:

**PostgreSQL:**
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

**Airflow:**
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`
- `AIRFLOW_CORE_FERNET_KEY`
- `AIRFLOW__WEBSERVER__SECRET_KEY`
- `AIRFLOW_WWW_USER_USERNAME`
- `AIRFLOW_WWW_USER_PASSWORD`
- `AZURE_KEYVAULT_URL` (optional)

**RabbitMQ:**
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`
- `RABBITMQ_DEFAULT_VHOST`
- `RABBITMQ_HOST`
- `RABBITMQ_PORT`
- `RABBITMQ_VHOST`
- `RABBITMQ_USER`
- `RABBITMQ_PASSWORD`
- `RABBITMQ_EXCHANGE` (optional)
- `RABBITMQ_ROUTING_KEY` (optional, default: rpa_events)

**RPA Database:**
- `RPA_DB_HOST`
- `RPA_DB_PORT`
- `RPA_DB_USER`
- `RPA_DB_PASSWORD`
- `RPA_DB_NAME`

**RPA API:**
- `RPA_API_PORT` (optional, default: 3000)

#### Loading Secrets

Before starting Docker Compose, run:
```powershell
. .\src\scripts\load-aws-secrets.ps1
```

This script:
- Fetches all secrets from AWS Secrets Manager
- Exports them as environment variables to the current PowerShell session
- Validates that critical variables are present
- Fails immediately if AWS authentication or secret retrieval fails

#### Security Notes
- **No `.env` files in production:** All secrets come from AWS Secrets Manager
- **Fast failure:** Services will not start if required secrets are missing
- **No secret caching:** Secrets are loaded fresh on each startup
- **AWS authentication required:** Ensure AWS CLI is configured before running
- **Local development:** `.env` files can still be used for local testing (excluded from production)

## 📋 Workflow Example

### New DAG: ecargo_pod_download
1. **Set Airflow Variable** `ECARGO_XLSX_PATH` with absolute path to `.xlsx` file
2. **Create HTTP Connection** `rpa_api` pointing to `http://rpa-api:3000`
3. **Trigger DAG** `ecargo_pod_download` manually in Airflow UI
4. **Task 1**: `convert_xls_to_json` - extracts NOTA FISCAL values from Excel
5. **Task 2**: `post_to_rpa_api` - POSTs payload to RPA API `/request_rpa_exec`
6. **API publishes** message to RabbitMQ queue
7. **RPA Listener** consumes message from queue
8. **Listener executes** Robot Framework test
9. **Results** saved to `rpa-robots/results/`

### Legacy Workflow (Deprecated)
1. **Create DAG** in Airflow UI or trigger manually
2. **DAG calls** RPA API `/request_rpa_exec` endpoint
3. **API publishes** message to RabbitMQ queue
4. **RPA Listener** consumes message from queue
5. **Listener executes** Robot Framework test
6. **Results** saved to `rpa-robots/results/`

## 🚨 Troubleshooting

### Common Issues

#### Docker Services Not Starting
```powershell
# Check Docker Desktop is running
docker --version

# Check service status
docker-compose ps

# View service logs
docker-compose logs rpa-api
docker-compose logs airflow-webserver
```

#### Python Virtual Environment Issues
```powershell
# Recreate virtual environments
cd rpa-listener
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Port Already in Use
```powershell
# Check what's using the port
netstat -ano | findstr :3000
netstat -ano | findstr :8080
# Kill process if needed
taskkill /PID <PID> /F
```

#### Environment Variables Not Loading
- Ensure AWS Secrets Manager script was run: `. .\src\scripts\load-aws-secrets.ps1`
- Verify AWS CLI is installed and configured: `aws --version`
- Check AWS credentials are valid: `aws sts get-caller-identity`
- Verify you have permission to access secret `dev/rpa-airflow` in region `eu-north-1`
- Ensure secrets are loaded in the same PowerShell session where Docker Compose runs
- For local development: Ensure `.env` file is in repository root (UTF-8 encoding, no spaces around `=`)

#### RPA Listener Not Connecting to RabbitMQ
```powershell
# Check if RabbitMQ is running
docker-compose ps rabbitmq

# Check RabbitMQ logs
docker-compose logs rabbitmq

# Verify environment variables
echo $env:RABBITMQ_HOST
echo $env:RABBITMQ_DEFAULT_USER
```

### Log Locations
- **Docker Logs**: `docker-compose logs -f <service-name>`
- **Airflow Logs**: `./airflow/logs/`
- **RPA Listener Logs**: PowerShell console output
- **Robot Results**: `./rpa-robots/results/`

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVM for Windows](https://github.com/coreybutler/nvm-windows)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [RabbitMQ Management](https://www.rabbitmq.com/management.html)
- [Robot Framework](https://robotframework.org/)
- [Apache Airflow](https://airflow.apache.org/)