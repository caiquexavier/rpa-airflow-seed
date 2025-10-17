@echo off
REM Batch script to run tests easily on Windows

echo Running RPA API Tests...
echo.

REM Set PYTHONPATH
set PYTHONPATH=src

REM Check if argument is provided
if "%1"=="" (
    echo Running all tests...
    python -m pytest tests/validations/ tests/test_executions_models.py --cov=src --cov-report=html --cov-report=term-missing -v
) else if "%1"=="unit" (
    echo Running unit tests...
    python -m pytest tests/validations/ tests/test_executions_models.py --cov=src --cov-report=html --cov-report=term-missing -v
) else if "%1"=="coverage" (
    echo Running tests with coverage report...
    python -m pytest tests/validations/ tests/test_executions_models.py --cov=src --cov-report=html --cov-report=term-missing -v
    echo.
    echo Coverage report generated in htmlcov/index.html
    start htmlcov/index.html
) else if "%1"=="help" (
    echo Usage: run-tests.bat [option]
    echo.
    echo Options:
    echo   unit      - Run unit tests only
    echo   coverage  - Run tests and open coverage report
    echo   help      - Show this help message
    echo   (no args) - Run all available tests
) else (
    echo Unknown option: %1
    echo Use 'run-tests.bat help' for usage information
)

echo.
echo Test execution completed.
