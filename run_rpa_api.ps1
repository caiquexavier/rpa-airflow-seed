# PowerShell script to run rpa-api locally
Write-Host "Starting rpa-api locally..." -ForegroundColor Green

# Change to rpa-api directory
Set-Location -Path "rpa-api"

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Set environment variables for RabbitMQ
$env:RABBITMQ_HOST = "localhost"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_USER = "admin"
$env:RABBITMQ_PASSWORD = "pass"
$env:RABBITMQ_VHOST = "/"
$env:RABBITMQ_QUEUE = "rpa_events"

# Start the API
Write-Host "Starting rpa-api server..." -ForegroundColor Green
Write-Host "API will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:3000/health" -ForegroundColor Cyan
Write-Host "RabbitMQ: $env:RABBITMQ_USER@$env:RABBITMQ_HOST:$env:RABBITMQ_PORT" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow

uvicorn src.main:app --reload --host 0.0.0.0 --port 3000
