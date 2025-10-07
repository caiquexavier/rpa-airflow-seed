# PowerShell script to run Robot Framework tests
Write-Host "Starting Robot Framework tests..." -ForegroundColor Green

# Change to rpa-robots directory
Set-Location -Path "rpa-robots"

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

# Initialize Robot Framework Browser (downloads Playwright/node deps if needed)
Write-Host "Initializing Robot Framework Browser..." -ForegroundColor Yellow
./venv/Scripts/rfbrowser.exe init

# Create results directory if it doesn't exist
if (-not (Test-Path "results")) {
    Write-Host "Creating results directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "results"
}

# Run Robot Framework tests
Write-Host "Running Robot Framework tests..." -ForegroundColor Green
Write-Host "Test results will be saved in: results/" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the tests" -ForegroundColor Yellow

# Run all tests in the tests directory
.\venv\Scripts\robot.exe -d results tests\

Write-Host "Tests completed! Check results/ directory for output files." -ForegroundColor Green
