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

### 3) Environment Setup
```powershell
# Run the setup script to configure environment and install dependencies
powershell -ExecutionPolicy Bypass -File scripts/setup-env.ps1
```

This script will:
- Load secrets from Azure Key Vault
- Create `.env` file with required configuration
- Set up Python virtual environments for both services
- Install all required dependencies

### 4) Start Services

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

### 5) Access Services
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **RPA API**: http://localhost:3000
- **RabbitMQ Management**: http://localhost:15672 (credentials from Key Vault)
- **API Health Check**: http://localhost:3000/health

### 6) Development Mode (Optional)
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
├── scripts/                  # PowerShell setup and management scripts
│   ├── setup-env.ps1         # Environment setup and dependency installation
│   └── start-listener.ps1    # PowerShell script to start RPA Listener
├── airflow/                   # Airflow orchestration
│   ├── Dockerfile             # Custom Airflow image
│   ├── dags/                  # Workflow definitions
│   │   ├── call_publish_api_dag.py
│   │   └── example_dag.py
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
└── config/                   # Configuration files
    └── rabbitmq/
        └── definitions.json  # RabbitMQ queue definitions
```

## 🔧 Features

### Airflow Orchestration
- **Custom Docker Image**: Pinned Apache Airflow 2.9.3 with Microsoft WinRM provider
- **LocalExecutor**: Single-node execution for development
- **PostgreSQL Backend**: Persistent metadata storage
- **DAG Management**: Visual workflow management at http://localhost:8080

### RPA API (FastAPI) - Docker Container
- **RESTful Endpoints**: `/publish`, `/health`
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
curl -X POST http://localhost:3000/publish -H "Content-Type: application/json" -d '{"rpa-id":"test-001"}'

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
curl -X POST http://localhost:3000/publish -H "Content-Type: application/json" -d '{"rpa-id":"docker-test-001"}'
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

### Environment Variables
- **RPA_API_PORT**: API port (default 3000)
- **RABBITMQ_HOST**: RabbitMQ host (default rabbitmq for Docker, localhost for listener)
- **RABBITMQ_PORT**: RabbitMQ port (default 5672)
- **RABBITMQ_DEFAULT_USER**: RabbitMQ username (default admin)
- **RABBITMQ_DEFAULT_PASS**: RabbitMQ password (default admin)
- **RABBITMQ_QUEUE**: Queue name (default rpa_events)
- **AZURE_KEYVAULT_URL**: Azure Key Vault URL (required)
- **AZURE_TENANT_ID**, **AZURE_CLIENT_ID**, **AZURE_CLIENT_SECRET**: Azure credentials

### Security Notes
- Change default credentials before production use
- Azure Key Vault integration for secure credential storage
- Environment variables for service configuration
- Keep credentials in `KEY=VALUE` format (no quotes)
- Docker containers use internal networking for service communication

## 📋 Workflow Example

1. **Create DAG** in Airflow UI or trigger manually
2. **DAG calls** RPA API `/publish` endpoint
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
- Ensure `.env` file is in repository root
- Check file encoding (should be UTF-8)
- Verify no spaces around `=` in `.env` file
- Restart Docker services after `.env` changes

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