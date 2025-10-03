# PowerShell script to run RPA Listener
Write-Host "Starting RPA Listener..." -ForegroundColor Green

# Change to rpa-listener directory
Set-Location -Path "rpa-listener"

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

# Set environment variables
$env:RABBITMQ_HOST = "localhost"
$env:RABBITMQ_USER = "admin"
$env:RABBITMQ_PASSWORD = "pass"
$env:RABBITMQ_QUEUE = "rpa_events"
$env:PROJECT_DIR = "C:\Users\caiqu\Documents\workspace\rpa-airflow-seed\rpa-robots"

# Start the listener
Write-Host "Starting RPA Listener..." -ForegroundColor Green
Write-Host "Listening for RabbitMQ messages..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

python main.py

