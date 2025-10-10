# RPA API

Minimal FastAPI service for queuing RPA execution requests via RabbitMQ.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy from `env.example`):
```bash
cp env.example .env
```

3. Update `.env` with your RabbitMQ settings:
```
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_EXCHANGE=
RABBITMQ_ROUTING_KEY=rpa_events
```

## Running

```bash
uvicorn src.main:app --host 0.0.0.0 --port 3000
```

## API Endpoints

### POST /request_rpa_exec

Queues an RPA execution request.

**Request Body:**
- `rpa_id` (required): Non-empty string identifier
- `callback_url` (optional): Valid URL for callbacks
- `rpa_request` (optional): JSON object with request data

**Response:**
- `202 Accepted`: Request queued successfully
- `400 Bad Request`: Validation errors
- `500 Internal Server Error`: Server error

## Testing with curl

### Valid enqueue

```bash
curl -sS -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{
    "rpa_id": "invoice_parser_v1",
    "callback_url": "http://localhost:3001/callback",
    "rpa_request": { "file_id": "abc123", "priority": "high" }
  }'
```

Expected **202**:
```json
{ "status":"queued", "rpa_id":"invoice_parser_v1", "has_callback": true }
```

### Missing rpa_id

```bash
curl -sS -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{ "rpa_request": { "k": "v" } }'
```

Expected **400** with errors for `rpa_id`.

### Unknown field

```bash
curl -sS -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{ "rpa_id": "x", "extra": 1 }'
```

Expected **400** with `"unexpected field 'extra'"`.

### Invalid URL

```bash
curl -sS -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{ "rpa_id": "x", "callback_url": "bad-url" }'
```

Expected **400** with URL error.

### Invalid rpa_request type

```bash
curl -sS -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{ "rpa_id": "x", "rpa_request": [] }'
```

Expected **400** with `"rpa_request must be a JSON object"`.