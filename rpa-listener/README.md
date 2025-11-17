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
$env:RABBITMQ_QUEUE = "RobotOperatorQueue"
$env:PROJECT_DIR = "C:\Users\caiqu\Documents\workspace\rpa-airflow-seed\rpa-robots"

# Windows CMD:
set AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
set RABBITMQ_HOST=localhost
set RABBITMQ_QUEUE=RobotOperatorQueue
set PROJECT_DIR=C:\Users\caiqu\Documents\workspace\rpa-airflow-seed\rpa-robots

# Linux/Mac:
export AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
export RABBITMQ_HOST=localhost
export RABBITMQ_QUEUE=RobotOperatorQueue
export PROJECT_DIR=/path/to/rpa-robots
```

### 5. Start the listener
```bash
python main.py
```

## AWS Secrets Manager Integration

The listener automatically loads AWS credentials from AWS Secrets Manager before running Robot Framework tests. This ensures S3 uploads work without manual environment variable setup.

**See [docs/README_AWS_SECRETS.md](docs/README_AWS_SECRETS.md) for detailed configuration.**

### Quick Setup

1. Ensure AWS credentials are configured (for accessing Secrets Manager):
   ```powershell
   aws configure
   # or
   $env:AWS_ACCESS_KEY_ID = "your-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret"
   ```

2. The secret `dev/rpa-airflow` (or value of `AWS_SECRET_NAME`) must contain:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_DEFAULT_REGION` (or `AWS_REGION`)
   - `AWS_S3_BUCKET`

3. The listener will automatically load these secrets when processing messages.

## Project Structure

The codebase follows a **Domain-Driven Architecture**:

```
src/
├── core/                    # Core infrastructure
│   └── config/             # Configuration modules
├── infrastructure/          # External integrations
│   ├── messaging/          # RabbitMQ consumer
│   ├── secrets/           # AWS Secrets Manager
│   └── http/              # HTTP clients (API, webhooks)
├── domain/                 # Business logic domains
│   ├── robot/             # Robot execution domain
│   ├── saga/              # Saga management domain
│   └── message/           # Message handling domain
└── application/           # Application layer (orchestration)
```

For detailed architecture documentation, see [docs/MIGRATION_SUMMARY.md](docs/MIGRATION_SUMMARY.md).

## Service Information
- **Purpose**: Listens for RabbitMQ messages and triggers RPA robot execution
- **Queue**: RobotOperatorQueue
- **Dependencies**: RabbitMQ server, AWS Secrets Manager access (for S3 credentials)

## Testing

Send a message to the `RobotOperatorQueue` queue with this JSON payload:
```json
{ "rpa_id": "job-001" }
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
- `RABBITMQ_QUEUE`: Queue name to listen to (default: RobotOperatorQueue)
- `PROJECT_DIR`: Path to Robot Framework project directory

## Features

- Connects to RabbitMQ and declares a durable queue
- Parses JSON messages with `rpa_id` field
- Runs Robot Framework tests via PowerShell
- Acknowledges messages on success, nacks on failure (no requeue)
- Graceful shutdown on Ctrl+C
- Comprehensive logging
