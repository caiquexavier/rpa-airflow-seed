# Load environment variables from AWS Secrets Manager
param(
    [string]$SecretName = "dev/rpa-airflow",
    [string]$Region = "eu-north-1"
)

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI not installed. Install from: https://aws.amazon.com/cli/"
    exit 1
}

# Function to validate and fix AWS credentials
function Test-AWSCredentials {
    param([string]$Region)
    
    $accessKey = $env:AWS_ACCESS_KEY_ID
    $secretKey = $env:AWS_SECRET_ACCESS_KEY
    $credentialsSource = "unknown"
    
    # Check AWS CLI config file
    $awsConfigPath = "$env:USERPROFILE\.aws\credentials"
    $awsConfigExists = Test-Path $awsConfigPath
    
    # Check if credentials are set in environment
    if ($accessKey -or $secretKey) {
        $credentialsSource = "environment"
        Write-Host "Checking AWS credentials from environment variables..." -ForegroundColor Cyan
        
        # Validate both are set
        if (-not $accessKey) {
            Write-Error "AWS_ACCESS_KEY_ID is not set in environment variables"
            return $false
        }
        if (-not $secretKey) {
            Write-Error "AWS_SECRET_ACCESS_KEY is not set in environment variables"
            return $false
        }
        
        # Trim whitespace (common issue causing signature errors)
        if ($accessKey) {
            $trimmedAccessKey = $accessKey.Trim()
            if ($accessKey -ne $trimmedAccessKey) {
                Write-Warning "AWS_ACCESS_KEY_ID has whitespace - trimming..."
                $env:AWS_ACCESS_KEY_ID = $trimmedAccessKey
                $accessKey = $trimmedAccessKey
            }
            if ($accessKey.Length -lt 16) {
                Write-Warning "AWS_ACCESS_KEY_ID seems too short ($($accessKey.Length) chars, expected ~20)"
            }
        }
        
        if ($secretKey) {
            $trimmedSecretKey = $secretKey.Trim()
            if ($secretKey -ne $trimmedSecretKey) {
                Write-Warning "AWS_SECRET_ACCESS_KEY has whitespace - trimming..."
                $env:AWS_SECRET_ACCESS_KEY = $trimmedSecretKey
                $secretKey = $trimmedSecretKey
            }
            if ($secretKey.Length -lt 20) {
                Write-Warning "AWS_SECRET_ACCESS_KEY seems too short ($($secretKey.Length) chars, expected ~40)"
            }
        }
    } elseif ($awsConfigExists) {
        $credentialsSource = "AWS CLI config"
        Write-Host "Checking AWS CLI configuration file..." -ForegroundColor Cyan
        Write-Host "  Found: $awsConfigPath" -ForegroundColor Gray
    } else {
        Write-Error "AWS credentials not found. Configure via:`n`n  1. Environment variables:`n     `$env:AWS_ACCESS_KEY_ID = 'your-access-key'.Trim()`n     `$env:AWS_SECRET_ACCESS_KEY = 'your-secret-key'.Trim()`n     `$env:AWS_DEFAULT_REGION = '$Region'`n`n  2. AWS CLI:`n     aws configure`n`nAfter setting credentials, run this script again."
        return $false
    }
    
    # Test credentials with STS (faster than Secrets Manager)
    Write-Host "Testing AWS credentials..." -ForegroundColor Cyan
    $stsTest = aws sts get-caller-identity --region $Region 2>&1
    if ($LASTEXITCODE -ne 0) {
        # Determine if credentials exist but are invalid, or don't exist
        $errorText = $stsTest -join "`n"
        $isInvalidToken = $errorText -match "InvalidClientTokenId|The security token included in the request is invalid"
        $isSignatureError = $errorText -match "SignatureDoesNotMatch|InvalidSignatureException"
        $isNoCredentials = $errorText -match "Unable to locate credentials|NoCredentialsError"
        
        if ($isInvalidToken) {
            Write-Error "AWS credentials are INVALID (InvalidClientTokenId).`n`nSource: $credentialsSource`nError: $errorText`n`nThis means the Access Key ID is invalid, expired, or doesn't exist.`n`nSOLUTION:`n  1. Get NEW credentials from AWS IAM Console:`n     - Go to AWS IAM Console (https://console.aws.amazon.com/iam/)`n     - Navigate to Users > Your User > Security credentials`n     - Create new Access Key (or use existing valid one)`n     - Copy the Access Key ID and Secret Access Key`n`n  2. Set them in PowerShell (with .Trim() to remove whitespace):`n     `$env:AWS_ACCESS_KEY_ID = 'NEW-ACCESS-KEY'.Trim()`n     `$env:AWS_SECRET_ACCESS_KEY = 'NEW-SECRET-KEY'.Trim()`n     `$env:AWS_DEFAULT_REGION = '$Region'`n`n  3. Or configure AWS CLI:`n     aws configure`n     (Enter the new credentials when prompted)`n`n  4. Test credentials:`n     aws sts get-caller-identity --region $Region`n`nCommon causes:`n  - Access Key ID is incorrect or has typos`n  - Access Key was deleted or deactivated in AWS`n  - Credentials are from wrong AWS account`n  - Credentials have hidden whitespace (use .Trim())`n  - Access Key ID format is wrong (should be ~20 characters)"
        } elseif ($isSignatureError) {
            Write-Error "AWS credentials are INVALID (signature mismatch).`n`nSource: $credentialsSource`nError: $errorText`n`nThis means credentials were found but they are WRONG.`n`nSOLUTION:`n  1. Get NEW credentials from AWS IAM Console:`n     - Go to AWS IAM Console`n     - Create new Access Key`n     - Copy the Access Key ID and Secret Access Key`n`n  2. Set them in PowerShell (with .Trim() to remove whitespace):`n     `$env:AWS_ACCESS_KEY_ID = 'NEW-ACCESS-KEY'.Trim()`n     `$env:AWS_SECRET_ACCESS_KEY = 'NEW-SECRET-KEY'.Trim()`n     `$env:AWS_DEFAULT_REGION = '$Region'`n`n  3. Or configure AWS CLI:`n     aws configure`n     (Enter the new credentials when prompted)`n`n  4. Test credentials:`n     aws sts get-caller-identity --region $Region`n`nCommon causes:`n  - Credentials are incorrect/expired`n  - Credentials have hidden whitespace (use .Trim())`n  - System clock is out of sync`n  - Credentials are from wrong AWS account"
        } elseif ($isNoCredentials) {
            Write-Error "AWS credentials not found. Configure via:`n`n  1. Environment variables:`n     `$env:AWS_ACCESS_KEY_ID = 'your-access-key'.Trim()`n     `$env:AWS_SECRET_ACCESS_KEY = 'your-secret-key'.Trim()`n     `$env:AWS_DEFAULT_REGION = '$Region'`n`n  2. AWS CLI:`n     aws configure`n`nError: $errorText"
        } else {
            Write-Error "Failed to validate AWS credentials.`n`nSource: $credentialsSource`nError: $errorText`n`nPlease check your AWS credentials and try again.`n`nCommon solutions:`n  1. Verify credentials in AWS IAM Console`n  2. Remove whitespace: `$env:AWS_ACCESS_KEY_ID = `$env:AWS_ACCESS_KEY_ID.Trim()`n  3. Test with: aws sts get-caller-identity --region $Region`n  4. Check system time: Get-Date (must be synchronized)"
        }
        return $false
    }
    
    Write-Host "AWS credentials validated successfully (source: $credentialsSource)" -ForegroundColor Green
    return $true
}

# Validate credentials before attempting to fetch secrets
if (-not (Test-AWSCredentials -Region $Region)) {
    exit 1
}

Write-Host "Fetching secrets: $SecretName" -ForegroundColor Cyan

try {
    $secretJson = aws secretsmanager get-secret-value --secret-id $SecretName --region $Region --query SecretString --output text 2>&1
    if ($LASTEXITCODE -ne 0) {
        # Check for specific error types
        if ($secretJson -match "InvalidSignatureException|SignatureDoesNotMatch") {
            Write-Error "AWS signature error - credentials are invalid.`n`nError: $secretJson`n`nSOLUTION:`n  1. Verify credentials are correct in AWS IAM Console`n  2. Remove whitespace: `$env:AWS_ACCESS_KEY_ID = `$env:AWS_ACCESS_KEY_ID.Trim()`n  3. Test with: aws sts get-caller-identity`n  4. If test fails, credentials are wrong - get new ones from AWS`n  5. Check system time: Get-Date (must be synchronized)"
        } elseif ($secretJson -match "AccessDeniedException") {
            Write-Error "Access denied to secret '$SecretName'.`n`nError: $secretJson`n`nCheck IAM permissions for secretsmanager:GetSecretValue on secret '$SecretName'"
        } elseif ($secretJson -match "ResourceNotFoundException") {
            Write-Error "Secret '$SecretName' not found in region '$Region'.`n`nError: $secretJson`n`nCheck secret name and region."
        } else {
            Write-Error "Failed to retrieve secret: $secretJson"
        }
        exit 1
    }

    $secret = $secretJson | ConvertFrom-Json
    $exportedCount = 0
    $envFileContent = @()
    
    $secret.PSObject.Properties | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_.Value)) { return }
        [Environment]::SetEnvironmentVariable($_.Name, $_.Value, "Process")
        $escapedValue = $_.Value -replace '\\', '\\' -replace '"', '\"' -replace "`n", '\n' -replace "`r", ''
        $envFileContent += "$($_.Name)=$escapedValue"
        $exportedCount++
    }
    
    $rootEnvPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) ".env"))
    $envFileContent -join "`n" | Out-File -FilePath $rootEnvPath -Encoding utf8 -NoNewline
    Add-Content -Path $rootEnvPath -Value "" -NoNewline
    
    Write-Host "Loaded $exportedCount variables from AWS Secrets Manager" -ForegroundColor Green
    Write-Host "Generated .env file: $rootEnvPath" -ForegroundColor Green
    
    # Verify critical variables
    $criticalVars = @("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", "AIRFLOW_CORE_FERNET_KEY", "AIRFLOW__WEBSERVER__SECRET_KEY", "AIRFLOW_WWW_USER_USERNAME", "AIRFLOW_WWW_USER_PASSWORD", "RABBITMQ_DEFAULT_USER", "RABBITMQ_DEFAULT_PASS", "RPA_DB_USER", "RPA_DB_PASSWORD", "RPA_DB_NAME", "OPENAI_API_KEY")
    $missing = $criticalVars | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_, "Process")) }
    
    if ($missing.Count -gt 0) {
        Write-Warning "Missing critical variables: $($missing -join ', ')"
    } else {
        Write-Host "All critical variables are set" -ForegroundColor Green
    }
} catch {
    Write-Error "Failed to parse secret: $_"
    exit 1
}
