# rpa-api

Minimal FastAPI service for RPA operations with RabbitMQ queue publishing.

## Features
- **POST /publish** - Publish messages to RabbitMQ queue
- **GET /health** - Health check endpoint
- **MVC Architecture** - Clean separation of concerns
- **Pydantic Validation** - Type-safe request validation
- **Environment Configuration** - Configurable RabbitMQ settings

## Requirements
- Python 3.10+
- RabbitMQ server

## Setup

### Environment Configuration
Copy `.env.example` to `.env` and configure your RabbitMQ settings:
```bash
cp .env.example .env
```

### Manual virtual environment
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On POSIX:
source venv/bin/activate

pip install -r requirements.txt
```

## Quick start

### Development server
```bash
# POSIX:
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# Windows (PowerShell):
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Quick Start Scripts
Use the provided scripts to run the API locally:

**Windows (PowerShell):**
```powershell
.\run_rpa_api.ps1
```

**Windows (Command Prompt):**
```cmd
run_rpa_api.bat
```

**Linux/macOS:**
```bash
./run_rpa_api.sh
```

The API will be available at `http://localhost:3000`.

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

## Configuration

The service uses environment variables for RabbitMQ configuration:

- `RABBITMQ_HOST` - RabbitMQ host (default: localhost)
- `RABBITMQ_PORT` - RabbitMQ port (default: 5672)
- `RABBITMQ_USER` - Username (default: guest)
- `RABBITMQ_PASSWORD` - Password (default: guest)
- `RABBITMQ_VHOST` - Virtual host (default: /)
- `RABBITMQ_EXCHANGE` - Exchange name (empty for direct queue)
- `RABBITMQ_ROUTING_KEY` - Routing key (required if exchange is set)
- `RABBITMQ_QUEUE` - Queue name (default: rpa_events)
- `RABBITMQ_PUBLISH_CONFIRM` - Enable publisher confirms (default: true)

**Note:** This project was refactored from "earthquakes" to "rpa" for minimal FastAPI implementation.