# PowerShell script to run tests with coverage
param(
    [string]$TestType = "all",
    [string]$CoverageThreshold = "80",
    [switch]$GenerateReport = $false,
    [switch]$Verbose = $false
)

Write-Host "Running RPA API Tests..." -ForegroundColor Green

# Set environment variables
$env:PYTHONPATH = "src"

# Install test dependencies if needed
if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
    Write-Host "Installing test dependencies..." -ForegroundColor Yellow
    pip install -r requirements-test.txt
}

# Base pytest command
$pytestCmd = "pytest"

# Add coverage options
$pytestCmd += " --cov=src --cov-report=term-missing --cov-fail-under=$CoverageThreshold"

# Add HTML report if requested
if ($GenerateReport) {
    $pytestCmd += " --cov-report=html:htmlcov --html=reports/test-report.html --self-contained-html"
    New-Item -ItemType Directory -Force -Path "reports" | Out-Null
}

# Add verbose output if requested
if ($Verbose) {
    $pytestCmd += " -v -s"
}

# Select test type
switch ($TestType) {
    "unit" { $pytestCmd += " -m unit" }
    "integration" { $pytestCmd += " -m integration" }
    "all" { }
    default { 
        Write-Host "Invalid test type. Use: unit, integration, or all" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Executing: $pytestCmd" -ForegroundColor Cyan
Invoke-Expression $pytestCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
    
    if ($GenerateReport) {
        Write-Host "Test report generated: reports/test-report.html" -ForegroundColor Green
        Write-Host "Coverage report generated: htmlcov/index.html" -ForegroundColor Green
    }
} else {
    Write-Host "Tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}
