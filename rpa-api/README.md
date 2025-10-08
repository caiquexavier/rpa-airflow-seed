# RPA API

Minimal FastAPI service for RPA operations with RabbitMQ queue publishing.

## Features
- **POST /publish** - Publish messages to RabbitMQ queue
- **GET /health** - Health check endpoint
- **MVC Architecture** - Clean separation of concerns
- **Pydantic Validation** - Type-safe request validation
- **Environment Configuration** - Configurable RabbitMQ settings

## Prerequisites
- Python 3.11+
- Virtual environment (venv)
- Dependencies installed
- RabbitMQ server running

## Quick Start

### 1. Navigate to rpa-api directory
```bash
cd rpa-api
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
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_VHOST = "/"
$env:RABBITMQ_QUEUE = "rpa_events"

# Windows CMD:
set AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
set RABBITMQ_HOST=localhost
set RABBITMQ_PORT=5672
set RABBITMQ_VHOST=/
set RABBITMQ_QUEUE=rpa_events

# Linux/Mac:
export AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_VHOST=/
export RABBITMQ_QUEUE=rpa_events
```

### 5. Start the API server
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 3000
```

## Service Endpoints
- **API**: http://localhost:3000
- **Health Check**: http://localhost:3000/health
- **API Documentation**: http://localhost:3000/docs

## API Endpoints

### Health Check
```bash
curl http://localhost:3000/health
```
Response:
```json
{"status": "ok"}
```

### Publish Message
```bash
curl -X POST http://localhost:3000/publish \
  -H "Content-Type: application/json" \
  -d '{"rpa-id":"job-001","anything":"else","nested":{"ok":true}}'
```
Response (202 Accepted):
```json
{"status": "queued", "rpa-id": "job-001"}
```

**Note:** Only the `rpa-id` field is sent to the RabbitMQ queue. Extra fields in the request are ignored for security and data cleanliness.

### Root Endpoint
```bash
curl http://localhost:3000/
```
Response:
```json
{"service": "rpa", "status": "ok"}
```

## Testing
```bash
pytest -q
```

## Project Structure
```
rpa-api/
├── src/
│   ├── controllers/
│   │   └── publish_controller.py    # API endpoints
│   ├── services/
│   │   └── queue_service.py         # Business logic
│   ├── libs/
│   │   └── rabbitmq_client.py       # RabbitMQ client
│   ├── validations/
│   │   └── publish_payload.py       # Pydantic models
│   └── main.py                      # FastAPI app
├── tests/
│   ├── test_publish_payload.py      # Validation tests
│   └── test_queue_service.py        # Service tests
├── requirements.txt
└── .env.example
```

## Docker Alternative
```bash
# Build and run with Docker
docker build -t rpa-api .
docker run -p 3000:3000 -e AZURE_KEYVAULT_URL=https://rpaidentity.vault.azure.net/ rpa-api
```

## Troubleshooting
- Ensure RabbitMQ is running and accessible
- Check Azure Key Vault credentials
- Verify all environment variables are set
- Check logs for detailed error messages

## Configuration

The service uses environment variables for RabbitMQ configuration:

- `AZURE_KEYVAULT_URL` - Azure Key Vault URL (required)
- `RABBITMQ_HOST` - RabbitMQ host (default: localhost)
- `RABBITMQ_PORT` - RabbitMQ port (default: 5672)
- `RABBITMQ_VHOST` - Virtual host (default: /)
- `RABBITMQ_EXCHANGE` - Exchange name (empty for direct queue)
- `RABBITMQ_ROUTING_KEY` - Routing key (required if exchange is set)
- `RABBITMQ_QUEUE` - Queue name (default: rpa_events)
- `RABBITMQ_PUBLISH_CONFIRM` - Enable publisher confirms (default: true)

**Note:** `RABBITMQ_USER` and `RABBITMQ_PASSWORD` are now retrieved from Azure Key Vault using the secret names `rabbitmq-user` and `rabbitmq-password`.