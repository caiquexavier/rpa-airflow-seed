# RPA Listener

A minimal Python listener that connects to RabbitMQ and runs Robot Framework tests via PowerShell.

## Prerequisites
- Python 3.11+
- Virtual environment (venv)
- Dependencies installed
- RabbitMQ server running

## Quick Start

### 1. Navigate to rpa-listener directory
```bash
cd rpa-listener
```

### 2. Create and activate virtual environment
```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables
```bash
# Windows PowerShell:
$env:AZURE_KEYVAULT_URL = "https://rpaidentity.vault.azure.net/"
$env:RABBITMQ_HOST = "localhost"
$env:RABBITMQ_QUEUE = "rpa_events"
$env:PROJECT_DIR = "C:\Users\caiqu\Documents\workspace\rpa-airflow-seed\rpa-robots"

# Windows CMD:
set AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
set RABBITMQ_HOST=localhost
set RABBITMQ_QUEUE=rpa_events
set PROJECT_DIR=C:\Users\caiqu\Documents\workspace\rpa-airflow-seed\rpa-robots

# Linux/Mac:
export AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
export RABBITMQ_HOST=localhost
export RABBITMQ_QUEUE=rpa_events
export PROJECT_DIR=/path/to/rpa-robots
```

### 5. Start the listener
```bash
python main.py
```

## Service Information
- **Purpose**: Listens for RabbitMQ messages and triggers RPA robot execution
- **Queue**: rpa_events
- **Dependencies**: RabbitMQ server, Azure Key Vault access

## Testing

Send a message to the `rpa_events` queue with this JSON payload:
```json
{ "rpa-id": "job-001" }
```

## Docker Alternative
```bash
# Build and run with Docker
docker build -t rpa-listener .
docker run -e AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/ -e RABBITMQ_HOST=localhost rpa-listener
```

## Troubleshooting
- Ensure RabbitMQ is running and accessible
- Check Azure Key Vault credentials
- Verify PROJECT_DIR points to correct rpa-robots location
- Check logs for detailed error messages
- Ensure rpa-robots directory exists and is accessible

## Configuration

- `RABBITMQ_HOST`: RabbitMQ server host (default: localhost)
- `RABBITMQ_QUEUE`: Queue name to listen to (default: rpa_events)
- `PROJECT_DIR`: Path to Robot Framework project directory

## Features

- Connects to RabbitMQ and declares a durable queue
- Parses JSON messages with `rpa-id` field
- Runs Robot Framework tests via PowerShell
- Acknowledges messages on success, nacks on failure (no requeue)
- Graceful shutdown on Ctrl+C
- Comprehensive logging
