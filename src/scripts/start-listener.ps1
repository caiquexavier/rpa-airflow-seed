# Start RPA listener service
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$ListenerDir = Join-Path $ProjectRoot "rpa-listener"
$LoadSecretsScript = Join-Path $ProjectRoot "src\scripts\load-aws-secrets.ps1"
$OriginalLocation = Get-Location

# Trap to return to original directory on termination
trap {
    Set-Location -Path $OriginalLocation
    break
}

try {
    if (-not (Test-Path $ListenerDir)) {
        Write-Host "RPA Listener directory not found: $ListenerDir" -ForegroundColor Red
        exit 1
    }

    # Fix AWS credentials (trim whitespace) before loading secrets
    Write-Host "Preparing AWS credentials..." -ForegroundColor Cyan
    if ($env:AWS_ACCESS_KEY_ID) {
        $trimmed = $env:AWS_ACCESS_KEY_ID.Trim()
        if ($env:AWS_ACCESS_KEY_ID -ne $trimmed) {
            Write-Host "Trimming whitespace from AWS_ACCESS_KEY_ID" -ForegroundColor Yellow
            $env:AWS_ACCESS_KEY_ID = $trimmed
        }
    }
    if ($env:AWS_SECRET_ACCESS_KEY) {
        $trimmed = $env:AWS_SECRET_ACCESS_KEY.Trim()
        if ($env:AWS_SECRET_ACCESS_KEY -ne $trimmed) {
            Write-Host "Trimming whitespace from AWS_SECRET_ACCESS_KEY" -ForegroundColor Yellow
            $env:AWS_SECRET_ACCESS_KEY = $trimmed
        }
    }

    # Optionally load AWS secrets if credentials are available
    # This is optional - listener can run without AWS secrets if robot tests don't need S3
    Set-Location -Path $ProjectRoot
    if (Test-Path $LoadSecretsScript) {
        $hasAwsCredentials = ($env:AWS_ACCESS_KEY_ID -and $env:AWS_SECRET_ACCESS_KEY) -or (Test-Path "$env:USERPROFILE\.aws\credentials")
        
        if ($hasAwsCredentials) {
            Write-Host "Attempting to load secrets from AWS Secrets Manager..." -ForegroundColor Cyan
            $secretNameArg = $null
            $regionArg = $null
            if ($env:AWS_SECRET_NAME) { $secretNameArg = $env:AWS_SECRET_NAME }
            if ($env:AWS_REGION) { $regionArg = $env:AWS_REGION }

            $secretsLoaded = $false
            if ($secretNameArg -and $regionArg) {
                & $LoadSecretsScript -SecretName $secretNameArg -Region $regionArg 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
            } elseif ($secretNameArg) {
                & $LoadSecretsScript -SecretName $secretNameArg 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
            } elseif ($regionArg) {
                & $LoadSecretsScript -Region $regionArg 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
            } else {
                & $LoadSecretsScript 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
            }
            
            if ($secretsLoaded) {
                Write-Host "AWS secrets loaded successfully" -ForegroundColor Green
            } else {
                Write-Host "Warning: Failed to load secrets from AWS Secrets Manager" -ForegroundColor Yellow
                Write-Host "  Continuing without AWS secrets (listener will use environment variables directly)" -ForegroundColor Yellow
                Write-Host "  If robot tests need S3 access, fix AWS credentials:" -ForegroundColor Yellow
                Write-Host "    .\src\scripts\fix-aws-credentials.ps1" -ForegroundColor White
            }
        } else {
            Write-Host "AWS credentials not found - skipping AWS Secrets Manager" -ForegroundColor Gray
            Write-Host "  Listener will use environment variables directly" -ForegroundColor Gray
        }
    } else {
        Write-Host "Warning: load-aws-secrets.ps1 not found at: $LoadSecretsScript" -ForegroundColor Yellow
    }

    Set-Location -Path $ListenerDir

    # Validate required environment variables from AWS Secrets Manager
    $missingVars = @()
    if (-not $env:RABBITMQ_HOST) { $missingVars += "RABBITMQ_HOST" }
    if (-not $env:RABBITMQ_PORT) { $missingVars += "RABBITMQ_PORT" }
    if (-not $env:RABBITMQ_DEFAULT_USER) { $missingVars += "RABBITMQ_DEFAULT_USER" } else { $env:RABBITMQ_USER = $env:RABBITMQ_DEFAULT_USER }
    if (-not $env:RABBITMQ_DEFAULT_PASS) { $missingVars += "RABBITMQ_DEFAULT_PASS" } else { $env:RABBITMQ_PASSWORD = $env:RABBITMQ_DEFAULT_PASS }
    if (-not $env:RABBITMQ_ROBOT_OPERATOR_QUEUE) { $missingVars += "RABBITMQ_ROBOT_OPERATOR_QUEUE" }

    if ($missingVars.Count -gt 0) {
        Write-Host "ERROR: Missing required variables: $($missingVars -join ', ')" -ForegroundColor Red
        Write-Host "Run: . .\src\scripts\load-aws-secrets.ps1 or set AWS_SECRET_NAME/AWS_REGION and rerun" -ForegroundColor Yellow
        exit 1
    }

    $VenvPath = Join-Path $ListenerDir "venv\Scripts\Activate.ps1"
    if (-not (Test-Path $VenvPath)) {
        Write-Host "Virtual environment not found: $VenvPath" -ForegroundColor Red
        exit 1
    }

    & $VenvPath
    $env:PYTHONPATH = $ListenerDir
    python main.py
} finally {
    Set-Location -Path $OriginalLocation
}
