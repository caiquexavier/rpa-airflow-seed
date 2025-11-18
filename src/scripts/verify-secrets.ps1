# Verify required environment variables are set
$criticalVars = @("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", "AIRFLOW_CORE_FERNET_KEY", "AIRFLOW__WEBSERVER__SECRET_KEY", "AIRFLOW_WWW_USER_USERNAME", "AIRFLOW_WWW_USER_PASSWORD", "RABBITMQ_DEFAULT_USER", "RABBITMQ_DEFAULT_PASS", "RPA_DB_USER", "RPA_DB_PASSWORD", "RPA_DB_NAME", "OPENAI_API_KEY")

Write-Host "Verifying environment variables..." -ForegroundColor Cyan

$missing = @()
foreach ($var in $criticalVars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        $missing += $var
        Write-Host "  [MISSING] $var" -ForegroundColor Red
    } else {
        Write-Host "  [OK] $var" -ForegroundColor Green
    }
}

Write-Host "`nSummary: Present: $($criticalVars.Count - $missing.Count), Missing: $($missing.Count)" -ForegroundColor $(if ($missing.Count -eq 0) { "Green" } else { "Red" })

if ($missing.Count -gt 0) {
    Write-Host "`nMissing: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Run: . .\src\scripts\load-aws-secrets.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "All critical variables are set!" -ForegroundColor Green
exit 0
