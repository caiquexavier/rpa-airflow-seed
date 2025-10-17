# RPA API

FastAPI service for RPA execution management with end-to-end correlation tracking.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy from `env.example`):
```bash
cp env.example .env
```

3. Update `.env` with your settings:
```
# RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_EXCHANGE=
RABBITMQ_ROUTING_KEY=rpa_events

# Database Configuration
RPA_DB_HOST=localhost
RPA_DB_PORT=5432
RPA_DB_USER=airflow
RPA_DB_PASSWORD=airflow
RPA_DB_NAME=rpa_db
```

## Running

```bash
uvicorn src.main:app --host 0.0.0.0 --port 3000
```

## API Endpoints

### POST /request_rpa_exec

Creates an RPA execution request and publishes to queue.

**Request Body:**
```json
{
  "rpa_key_id": "job-001",
  "callback_url": "http://localhost:3000/updateRpaExecution",
  "rpa_request": { "nota_fiscal": "12345" }
}
```

**Response (202 Accepted):**
```json
{
  "exec_id": 123,
  "rpa_key_id": "job-001",
  "status": "ENQUEUED",
  "message": "Execution accepted",
  "published": true
}
```

### POST /updateRpaExecution

Updates RPA execution status (webhook endpoint).

**Request Body:**
```json
{
  "exec_id": 123,
  "rpa_key_id": "job-001",
  "rpa_response": { "files": ["pod.pdf"] },
  "status": "SUCCESS",
  "error_message": null
}
```

**Response (200 OK):**
```json
{
  "exec_id": 123,
  "updated": true,
  "status": "SUCCESS"
}
```

**Status Values:**
- `PENDING`: Initial state
- `RUNNING`: Execution in progress
- `SUCCESS`: Execution completed successfully
- `FAIL`: Execution failed

## Testing with curl

### 1. Request RPA Execution

```bash
curl -s -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{
    "rpa_key_id": "job-001",
    "callback_url": "http://localhost:3000/updateRpaExecution",
    "rpa_request": {"nota_fiscal": "12345"}
  }'
```

**Expected Response (202):**
```json
{
  "exec_id": 123,
  "rpa_key_id": "job-001",
  "status": "ENQUEUED",
  "message": "Execution accepted",
  "published": true
}
```

### 2. Update Execution Status (Success)

```bash
curl -s -X POST http://localhost:3000/updateRpaExecution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 123,
    "rpa_key_id": "job-001",
    "rpa_response": {"files": ["pod.pdf"]},
    "status": "SUCCESS",
    "error_message": null
  }'
```

**Expected Response (200):**
```json
{
  "exec_id": 123,
  "updated": true,
  "status": "SUCCESS"
}
```

### 3. Update Execution Status (Failure)

```bash
curl -s -X POST http://localhost:3000/updateRpaExecution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 123,
    "rpa_key_id": "job-001",
    "rpa_response": {"trace": "..."},
    "status": "FAIL",
    "error_message": "Selector not found: #notaFiscal"
  }'
```

### 4. Validation Errors

**Missing rpa_key_id:**
```bash
curl -s -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{"rpa_request": {"k": "v"}}'
```
Expected **422** validation error.

**Invalid callback URL:**
```bash
curl -s -X POST http://localhost:3000/request_rpa_exec \
  -H "Content-Type: application/json" \
  -d '{"rpa_key_id": "job-001", "callback_url": "not-a-url"}'
```
Expected **422** validation error.

**FAIL without error_message:**
```bash
curl -s -X POST http://localhost:3000/updateRpaExecution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 123,
    "rpa_key_id": "job-001",
    "rpa_response": {},
    "status": "FAIL"
  }'
```
Expected **422** validation error.

## Database Schema

The service uses the `rpa_automation_exec` table with the following structure:

- `exec_id` (PK): Auto-generated execution ID
- `rpa_key_id` (TEXT): RPA identifier
- `callback_url` (TEXT): Optional callback URL
- `rpa_request` (JSONB): Request payload
- `rpa_response` (JSONB): Response payload (filled by webhook)
- `exec_status` (TEXT): PENDING | RUNNING | SUCCESS | FAIL
- `error_message` (TEXT): Error details for failed executions
- `created_at` (TIMESTAMPTZ): Creation timestamp
- `updated_at` (TIMESTAMPTZ): Last update timestamp
- `finished_at` (TIMESTAMPTZ): Completion timestamp

## Execution Flow

1. **Request**: Client calls `/request_rpa_exec` with RPA details
2. **Database**: Execution record created with `PENDING` status
3. **Queue**: Message published to RabbitMQ with `exec_id`
4. **Status**: Execution status updated to `RUNNING`
5. **Processing**: rpa-listener processes message and runs robot
6. **Callback**: Robot calls `/updateRpaExecution` with results
7. **Completion**: Status updated to `SUCCESS` or `FAIL` with response data