@echo off
REM Batch script to run tests on Windows
setlocal

set PYTHONPATH=.;rpa-api;rpa-listener;airflow

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ and ensure it's in your PATH
    exit /b 1
)

if "%1"=="install" (
    echo Installing test dependencies...
    python -m pip install -r tests/requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        exit /b 1
    )
    echo Dependencies installed successfully!
    goto :end
)

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pytest is not installed
    echo Please run: tests\run-tests.bat install
    exit /b 1
)

if "%1"=="unit" (
    echo Running unit tests only...
    python -m pytest tests -v -m unit
    goto :end
)

if "%1"=="cov" (
    echo Running tests with coverage...
    python -m pytest tests --cov --cov-report=term-missing
    goto :end
)

if "%1"=="html" (
    echo Generating HTML coverage report...
    python -m pytest tests --cov --cov-report=html
    echo Coverage report generated in htmlcov/index.html
    goto :end
)

echo Running all tests...
python -m pytest tests -v

:end
endlocal

