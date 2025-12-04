#!/bin/bash
set -e

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill -TERM "$FASTAPI_PID" 2>/dev/null || true
    kill -TERM "$AIRFLOW_PID" 2>/dev/null || true
    wait "$FASTAPI_PID" 2>/dev/null || true
    wait "$AIRFLOW_PID" 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start FastAPI in the background
echo "Starting FastAPI server on port 8000..."
cd /opt/airflow
# Use --reload for development to pick up code changes
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start Airflow webserver in the background
echo "Starting Airflow webserver on port 8080..."
airflow webserver &
AIRFLOW_PID=$!

# Wait for both processes
wait $FASTAPI_PID $AIRFLOW_PID


