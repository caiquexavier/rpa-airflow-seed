# PowerShell script to run tests on Windows
param(
    [Parameter(Position=0)]
    [ValidateSet("all", "unit", "cov", "html", "install")]
    [string]$Command = "all"
)

$ErrorActionPreference = "Stop"

# Set Python path - use parent directories so relative imports work
$env:PYTHONPATH = ".;rpa-api;rpa-listener;airflow"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Function to check if Python is available
function Test-Python {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Function to check if pytest is installed
function Test-Pytest {
    try {
        $result = python -m pytest --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Check Python first
if (-not (Test-Python)) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ and ensure it's in your PATH" -ForegroundColor Yellow
    exit 1
}

switch ($Command) {
    "install" {
        Write-Host "Installing test dependencies..." -ForegroundColor Cyan
        python -m pip install -r tests/requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
            exit 1
        }
        Write-Host "Dependencies installed successfully!" -ForegroundColor Green
    }
    default {
        # Check if pytest is installed
        if (-not (Test-Pytest)) {
            Write-Host "ERROR: pytest is not installed" -ForegroundColor Red
            Write-Host "Please run: .\tests\run-tests.ps1 install" -ForegroundColor Yellow
            exit 1
        }
        
        switch ($Command) {
            "all" {
                Write-Host "Running all tests..." -ForegroundColor Cyan
                python -m pytest tests -v
            }
            "unit" {
                Write-Host "Running unit tests only..." -ForegroundColor Cyan
                python -m pytest tests -v -m unit
            }
            "cov" {
                Write-Host "Running tests with coverage..." -ForegroundColor Cyan
                python -m pytest tests --cov --cov-report=term-missing
            }
            "html" {
                Write-Host "Generating HTML coverage report..." -ForegroundColor Cyan
                python -m pytest tests --cov --cov-report=html
                Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor Green
            }
        }
    }
}

