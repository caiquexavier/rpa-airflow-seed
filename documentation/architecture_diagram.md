# RPA-Airflow Seed Architecture Diagram

## System Overview

The RPA-Airflow seed is a complete RPA orchestration platform that combines Apache Airflow for workflow orchestration, FastAPI for API services, RabbitMQ for message queuing, and Robot Framework for browser automation.

## Architecture Components

### 1. **Airflow Orchestration Layer**
- **Airflow Web Server** (localhost:8080)
- **Airflow Scheduler** 
- **Airflow Init** (Database initialization)
- **DAGs**: Workflow definitions (`dag_ecargo_pod_download.py`)
- **Custom Libraries**: Excel to RPA request converter

### 2. **RPA API Service** (FastAPI - Docker Container)
- **Port**: 3000
- **Endpoints**: 
  - `POST /request_rpa_exec` - Request RPA execution
  - `POST /updateRpaExecution` - Webhook for status updates
  - `GET /health` - Health check
- **Features**: Pydantic validation, RabbitMQ publishing, PostgreSQL integration

### 3. **RPA Listener** (PowerShell Worker)
- **Type**: RabbitMQ Consumer
- **Function**: Processes queued RPA jobs
- **Integration**: Executes Robot Framework tests
- **Environment**: PowerShell with Python virtual environment

### 4. **Robot Framework Automation**
- **Browser Testing**: Playwright-based automation
- **Test Suite**: `ecargo_pod_download.robot`
- **Resources**: Reusable keywords and browser automation
- **Results**: HTML reports and execution logs

### 5. **Message Queue System**
- **RabbitMQ** (localhost:15672)
- **Queue**: `rpa_events`
- **Management UI**: Web interface for monitoring
- **Durability**: Persistent message storage

### 6. **Database Layer**
- **PostgreSQL** (localhost:5432)
- **Airflow Database**: Metadata storage
- **RPA Database**: Execution tracking
- **Migrations**: Alembic for schema management

## Data Flow

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

## Workflow Process

### 1. **Excel Processing Workflow**
1. **Airflow DAG** reads Excel file (`Controle_Unilever_Personalizado.xlsx`)
2. **Converter** extracts NOTA FISCAL values from Excel
3. **HTTP Operator** POSTs payload to RPA API
4. **API** creates execution record and publishes to RabbitMQ
5. **Listener** consumes message and executes Robot Framework test
6. **Robot** performs browser automation (e-Cargo login, PDF downloads)
7. **Webhook** reports execution status back to API

### 2. **Message Flow**
```
Airflow → RPA API → RabbitMQ → RPA Listener → Robot Framework → Webhook → RPA API
```

## Technology Stack

### **Orchestration**
- Apache Airflow 2.9.3
- LocalExecutor
- Custom Docker image with WinRM provider

### **API Layer**
- FastAPI
- Pydantic validation
- Docker containerized
- Health checks

### **Message Queue**
- RabbitMQ 3.13-management
- Durable queues
- Web management interface

### **Automation**
- Robot Framework
- Playwright browser automation
- Selenium WebDriver
- PowerShell integration

### **Database**
- PostgreSQL 15
- Alembic migrations
- Dual database setup (Airflow + RPA)

### **Infrastructure**
- Docker Compose orchestration
- PowerShell scripts
- Environment variable management
- Azure Key Vault integration

## Service Dependencies

```
PostgreSQL ← Airflow (Web Server, Scheduler, Init)
     ↑
     └── RPA API ← RabbitMQ
                    ↑
                    └── RPA Listener → Robot Framework
```

## Port Configuration

- **Airflow UI**: 8080
- **RPA API**: 3000
- **RabbitMQ**: 5672 (AMQP), 15672 (Management)
- **PostgreSQL**: 5432

## Key Features

### **Orchestration**
- Visual workflow management
- DAG-based task scheduling
- Excel file processing
- HTTP API integration

### **API Services**
- RESTful endpoints
- Request validation
- Execution tracking
- Webhook support

### **Message Queue**
- Reliable message delivery
- Queue monitoring
- Auto-reconnection
- Persistent storage

### **Browser Automation**
- Cross-browser support
- Screenshot capture
- Error handling
- Results reporting

### **Monitoring**
- Health checks
- Log aggregation
- Execution tracking
- Error reporting

## Security Features

- Azure Key Vault integration
- Environment variable management
- Credential encryption
- Secure service communication

## Development Workflow

1. **Setup**: PowerShell scripts configure environment
2. **Development**: Individual service development
3. **Testing**: Robot Framework test execution
4. **Deployment**: Docker Compose orchestration
5. **Monitoring**: Web interfaces and logs

This architecture provides a complete, production-ready RPA orchestration platform with robust error handling, monitoring, and scalability features.
