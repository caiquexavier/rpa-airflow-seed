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

    # Load AWS secrets first so required env vars are available
    Set-Location -Path $ProjectRoot
    if (Test-Path $LoadSecretsScript) {
        Write-Host "Loading secrets from AWS Secrets Manager..." -ForegroundColor Cyan
        $secretNameArg = $null
        $regionArg = $null
        if ($env:AWS_SECRET_NAME) { $secretNameArg = $env:AWS_SECRET_NAME }
        if ($env:AWS_REGION) { $regionArg = $env:AWS_REGION }

        $secretsLoaded = $false
        if ($secretNameArg -and $regionArg) {
            & $LoadSecretsScript -SecretName $secretNameArg -Region $regionArg
            if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
        } elseif ($secretNameArg) {
            & $LoadSecretsScript -SecretName $secretNameArg
            if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
        } elseif ($regionArg) {
            & $LoadSecretsScript -Region $regionArg
            if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
        } else {
            & $LoadSecretsScript
            if ($LASTEXITCODE -eq 0) { $secretsLoaded = $true }
        }
        
        if (-not $secretsLoaded) {
            Write-Host "`nFailed to load secrets from AWS Secrets Manager" -ForegroundColor Red
            Write-Host "Please fix AWS credentials and try again. Run:" -ForegroundColor Yellow
            Write-Host "  .\src\scripts\fix-aws-credentials.ps1" -ForegroundColor Yellow
            Write-Host "Or manually fix credentials:" -ForegroundColor Yellow
            Write-Host "  `$env:AWS_ACCESS_KEY_ID = 'your-key'.Trim()" -ForegroundColor White
            Write-Host "  `$env:AWS_SECRET_ACCESS_KEY = 'your-secret'.Trim()" -ForegroundColor White
            exit 1
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
    if (-not $env:RABBITMQ_QUEUE) { $missingVars += "RABBITMQ_QUEUE" }

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
