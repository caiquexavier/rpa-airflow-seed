# Helper script to diagnose and fix AWS credential issues
# This script helps identify common problems with AWS credentials

Write-Host "AWS Credentials Diagnostic Tool" -ForegroundColor Cyan
Write-Host "==============================`n" -ForegroundColor Cyan

# Check if AWS CLI is installed
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] AWS CLI not installed" -ForegroundColor Red
    Write-Host "Install from: https://aws.amazon.com/cli/`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] AWS CLI is installed`n" -ForegroundColor Green

# Check environment variables
$accessKey = $env:AWS_ACCESS_KEY_ID
$secretKey = $env:AWS_SECRET_ACCESS_KEY
$region = $env:AWS_DEFAULT_REGION

Write-Host "Environment Variables:" -ForegroundColor Cyan
if ($accessKey) {
    $trimmed = $accessKey.Trim()
    if ($accessKey -ne $trimmed) {
        Write-Host "  [WARNING] AWS_ACCESS_KEY_ID has whitespace (length: $($accessKey.Length))" -ForegroundColor Yellow
        Write-Host "            Original: '$accessKey'" -ForegroundColor Yellow
        Write-Host "            Trimmed:  '$trimmed'" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] AWS_ACCESS_KEY_ID is set (length: $($accessKey.Length))" -ForegroundColor Green
    }
} else {
    Write-Host "  [MISSING] AWS_ACCESS_KEY_ID not set" -ForegroundColor Red
}

if ($secretKey) {
    $trimmed = $secretKey.Trim()
    if ($secretKey -ne $trimmed) {
        Write-Host "  [WARNING] AWS_SECRET_ACCESS_KEY has whitespace (length: $($secretKey.Length))" -ForegroundColor Yellow
        Write-Host "            Original: '$($secretKey.Substring(0, [Math]::Min(10, $secretKey.Length)))...'" -ForegroundColor Yellow
        Write-Host "            Trimmed:  '$($trimmed.Substring(0, [Math]::Min(10, $trimmed.Length)))...'" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] AWS_SECRET_ACCESS_KEY is set (length: $($secretKey.Length))" -ForegroundColor Green
    }
} else {
    Write-Host "  [MISSING] AWS_SECRET_ACCESS_KEY not set" -ForegroundColor Red
}

if ($region) {
    Write-Host "  [OK] AWS_DEFAULT_REGION is set: $region" -ForegroundColor Green
} else {
    Write-Host "  [INFO] AWS_DEFAULT_REGION not set (will use default or eu-north-1)" -ForegroundColor Yellow
}

Write-Host ""

# Check AWS CLI configuration
Write-Host "AWS CLI Configuration:" -ForegroundColor Cyan
$awsConfig = aws configure list 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $awsConfig
} else {
    Write-Host "  [INFO] AWS CLI not configured (or using environment variables)" -ForegroundColor Yellow
}

Write-Host ""

# Test credentials
Write-Host "Testing Credentials:" -ForegroundColor Cyan
$testRegion = if ($region) { $region } else { "eu-north-1" }
$identity = aws sts get-caller-identity --region $testRegion 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [SUCCESS] Credentials are valid!" -ForegroundColor Green
    Write-Host $identity
} else {
    $errorText = $identity -join "`n"
    $isSignatureError = $errorText -match "SignatureDoesNotMatch|InvalidSignatureException"
    
    Write-Host "  [FAILED] Credentials test failed" -ForegroundColor Red
    Write-Host "  Error: $errorText" -ForegroundColor Red
    Write-Host ""
    
    if ($isSignatureError) {
        Write-Host "  [DIAGNOSIS] Signature mismatch detected - credentials are INVALID" -ForegroundColor Red
        Write-Host "  This means credentials were found but they are WRONG or EXPIRED.`n" -ForegroundColor Yellow
        Write-Host "SOLUTION - Get NEW credentials from AWS:" -ForegroundColor Cyan
        Write-Host "  1. Go to AWS IAM Console: https://console.aws.amazon.com/iam/" -ForegroundColor White
        Write-Host "  2. Navigate to: Users > [Your User] > Security credentials" -ForegroundColor White
        Write-Host "  3. Create new Access Key (or use existing valid one)" -ForegroundColor White
        Write-Host "  4. Copy the Access Key ID and Secret Access Key`n" -ForegroundColor White
        Write-Host "Then set them in PowerShell:" -ForegroundColor Cyan
        Write-Host "  `$env:AWS_ACCESS_KEY_ID = 'NEW-ACCESS-KEY'.Trim()" -ForegroundColor White
        Write-Host "  `$env:AWS_SECRET_ACCESS_KEY = 'NEW-SECRET-KEY'.Trim()" -ForegroundColor White
        Write-Host "  `$env:AWS_DEFAULT_REGION = '$testRegion'`n" -ForegroundColor White
        Write-Host "Or configure AWS CLI:" -ForegroundColor Cyan
        Write-Host "  aws configure" -ForegroundColor White
        Write-Host "  (Enter the new credentials when prompted)`n" -ForegroundColor White
        Write-Host "Test again:" -ForegroundColor Cyan
        Write-Host "  aws sts get-caller-identity --region $testRegion`n" -ForegroundColor White
    } else {
        Write-Host "Common Solutions:" -ForegroundColor Yellow
        Write-Host "  1. If credentials have whitespace, run:" -ForegroundColor Yellow
        Write-Host "     `$env:AWS_ACCESS_KEY_ID = `$env:AWS_ACCESS_KEY_ID.Trim()" -ForegroundColor White
        Write-Host "     `$env:AWS_SECRET_ACCESS_KEY = `$env:AWS_SECRET_ACCESS_KEY.Trim()" -ForegroundColor White
        Write-Host ""
        Write-Host "  2. If credentials are wrong, get new ones from AWS IAM Console" -ForegroundColor Yellow
        Write-Host "     Then set:" -ForegroundColor Yellow
        Write-Host "     `$env:AWS_ACCESS_KEY_ID = 'your-new-access-key'" -ForegroundColor White
        Write-Host "     `$env:AWS_SECRET_ACCESS_KEY = 'your-new-secret-key'" -ForegroundColor White
        Write-Host ""
        Write-Host "  3. Or configure AWS CLI:" -ForegroundColor Yellow
        Write-Host "     aws configure" -ForegroundColor White
        Write-Host ""
        Write-Host "  4. Check system time (must be synchronized):" -ForegroundColor Yellow
        Write-Host "     Get-Date" -ForegroundColor White
    }
}

Write-Host ""

# Check system time
Write-Host "System Time:" -ForegroundColor Cyan
$systemTime = Get-Date
Write-Host "  Current time: $systemTime" -ForegroundColor $(if ($systemTime) { "Green" } else { "Red" })

Write-Host ""

