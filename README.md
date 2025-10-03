# RPA Airflow Seed — Complete RPA Orchestration Platform

A production-ready platform for orchestrating RPA workloads with Apache Airflow, featuring a complete message queue system and browser automation capabilities.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Airflow UI    │    │   RPA API       │    │  RPA Listener   │
│  (Orchestrator) │───▶│  (FastAPI)      │───▶│  (Worker)       │
│  localhost:8080 │    │  localhost:3000 │    │  (RabbitMQ)     │
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

### Prerequisites (Windows)
- Git, Docker Desktop
- Python 3.11+
- PowerShell 7
- Google Chrome or Microsoft Edge

### 1. Start All Services
```powershell
# Start Airflow + PostgreSQL + RabbitMQ
docker compose up airflow-init
docker compose up -d

# Access Airflow UI: http://localhost:8080 (admin/admin)
# Access RabbitMQ Management: http://localhost:15672 (admin/pass)
```

### 2. Setup RPA API
```powershell
.\run_rpa_api.ps1
# API available at: http://localhost:3000
```

### 3. Setup RPA Listener
```powershell
.\run_rpa_listener.ps1
# Listener will process messages from RabbitMQ
```

### 4. Run Robot Tests
```powershell
.\run_robot.ps1
# Tests run in rpa-robots/ directory
```

## 📁 Project Structure

```
rpa-airflow-seed/
├── airflow/                    # Airflow orchestration
│   ├── Dockerfile             # Custom Airflow image
│   ├── dags/                  # Workflow definitions
│   │   ├── call_publish_api_dag.py
│   │   └── example_dag.py
│   └── logs/                  # Airflow logs
├── rpa-api/                   # FastAPI service
│   ├── src/
│   │   ├── controllers/       # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── libs/             # RabbitMQ client
│   │   └── validations/      # Request validation
│   └── requirements.txt
├── rpa-listener/              # Message queue worker
│   ├── main.py               # RabbitMQ listener
│   └── requirements.txt
├── rpa-robots/               # Robot Framework tests
│   ├── tests/                # Test suites
│   ├── resources/            # Reusable keywords
│   ├── variables/            # Shared variables
│   └── results/              # Test outputs
├── docker-compose.yml        # All services
└── *.ps1                     # PowerShell scripts
```

## 🔧 Features

### Airflow Orchestration
- **Custom Docker Image**: Pinned Apache Airflow 2.9.3 with Microsoft WinRM provider
- **LocalExecutor**: Single-node execution for development
- **PostgreSQL Backend**: Persistent metadata storage
- **DAG Management**: Visual workflow management at http://localhost:8080

### RPA API (FastAPI)
- **RESTful Endpoints**: `/publish`, `/health`
- **RabbitMQ Integration**: Message queue publishing
- **Pydantic Validation**: Type-safe request handling
- **MVC Architecture**: Clean separation of concerns

### RPA Listener (Worker)
- **RabbitMQ Consumer**: Processes queued RPA jobs
- **PowerShell Integration**: Executes Robot Framework tests
- **Error Handling**: Graceful failure management
- **Auto-reconnection**: Resilient message processing

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

## 🛠️ Common Commands

### Development
```powershell
# Run individual services
.\run_rpa_api.ps1          # Start API server
.\run_rpa_listener.ps1     # Start message worker
.\run_robot.ps1            # Run automation tests

# Docker management
docker compose up -d       # Start all services
docker compose down        # Stop all services
docker compose logs -f     # View logs
```

### Testing
```powershell
# Test API endpoints
curl http://localhost:3000/health
curl -X POST http://localhost:3000/publish -H "Content-Type: application/json" -d '{"rpa-id":"test-001"}'

# Run Robot tests
cd rpa-robots
.\venv\Scripts\robot.exe -d results tests
```

### Monitoring
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **RabbitMQ Management**: http://localhost:15672 (admin/pass)
- **API Health**: http://localhost:3000/health
- **Test Results**: `rpa-robots/results/`

## 🔐 Configuration

### Environment Variables
- **Airflow**: Configured in `docker-compose.yml`
- **RPA API**: Set in `run_rpa_api.ps1`
- **RPA Listener**: Set in `run_rpa_listener.ps1`

### Security Notes
- Change default credentials before production use
- Use `.env` files for sensitive configuration
- Keep credentials in `KEY=VALUE` format (no quotes)

## 📋 Workflow Example

1. **Create DAG** in Airflow UI or trigger manually
2. **DAG calls** RPA API `/publish` endpoint
3. **API publishes** message to RabbitMQ queue
4. **RPA Listener** consumes message from queue
5. **Listener executes** Robot Framework test
6. **Results** saved to `rpa-robots/results/`
