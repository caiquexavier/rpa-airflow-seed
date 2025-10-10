# PowerShell script to start the rpa-listener service
# This script activates the virtual environment and runs the listener

Write-Host "Starting RPA Listener..." -ForegroundColor Green

# Get the script directory and navigate to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$ListenerDir = Join-Path $ProjectRoot "rpa-listener"

Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "Listener directory: $ListenerDir" -ForegroundColor Cyan

# Check if rpa-listener directory exists
if (-not (Test-Path $ListenerDir)) {
    Write-Host "RPA Listener directory not found at: $ListenerDir" -ForegroundColor Red
    Write-Host "Please ensure the rpa-listener directory exists in the project root." -ForegroundColor Red
    exit 1
}

# Change to the rpa-listener directory
Set-Location -Path $ListenerDir

# Check if virtual environment exists
$VenvPath = Join-Path $ListenerDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $VenvPath
    
    # Set Python path
    $env:PYTHONPATH = $ListenerDir
    
    Write-Host "Starting listener service..." -ForegroundColor Yellow
    python main.py
} else {
    Write-Host "Virtual environment not found. Please run setup first." -ForegroundColor Red
    Write-Host "Expected path: $VenvPath" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Red
    exit 1
}
