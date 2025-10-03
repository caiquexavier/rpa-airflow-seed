# RPA Listener

A minimal Python listener that connects to RabbitMQ and runs Robot Framework tests via PowerShell.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r rpa-listener\requirements.txt
```

2. Copy and configure environment variables:
```bash
copy rpa-listener\.env.example .env
```

Edit `.env` and set the correct `PROJECT_DIR` path to your Robot Framework project.

## Usage

Run the listener:
```bash
.\venv\Scripts\python.exe rpa-listener\main.py
```

## Testing

Send a message to the `rpa_events` queue with this JSON payload:
```json
{ "rpa-id": "job-001" }
```

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
