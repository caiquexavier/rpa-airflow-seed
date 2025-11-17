# Test script for request_robot_execution endpoint
# This endpoint now requires exec_id as a direct parameter

# Replace EXEC_ID with a valid execution ID from your database
# You can get one by checking the execution table or from a saga creation response

$EXEC_ID = 1  # Replace with actual exec_id
$API_URL = "http://localhost:3000/api/v1/execution/request_robot_execution"

Write-Host "Testing request_robot_execution endpoint with exec_id=$EXEC_ID" -ForegroundColor Cyan
Write-Host ""

# Test 1: Minimal request with only exec_id (saga will be fetched from database)
Write-Host "Test 1: Minimal request with exec_id only" -ForegroundColor Yellow
$body1 = @{
    exec_id = $EXEC_ID
} | ConvertTo-Json

try {
    $response1 = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body1 -ContentType "application/json"
    Write-Host "Success:" -ForegroundColor Green
    $response1 | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}
Write-Host "`n"

# Test 2: Request with exec_id and callback_path
Write-Host "Test 2: Request with exec_id and callback_path" -ForegroundColor Yellow
$body2 = @{
    exec_id = $EXEC_ID
    callback_path = "/trigger/upload_nf_files_to_s3"
} | ConvertTo-Json

try {
    $response2 = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body2 -ContentType "application/json"
    Write-Host "Success:" -ForegroundColor Green
    $response2 | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}
Write-Host "`n"

# Test 3: Request with exec_id, callback_path, and saga (backward compatibility)
Write-Host "Test 3: Request with exec_id, callback_path, and saga (backward compatibility)" -ForegroundColor Yellow
$body3 = @{
    exec_id = $EXEC_ID
    callback_path = "/trigger/upload_nf_files_to_s3"
    saga = @{
        saga_id = 1
        exec_id = $EXEC_ID
        rpa_key_id = "rpa_protocolo_devolucao"
        data = @{}
        current_state = "PENDING"
    }
} | ConvertTo-Json -Depth 10

try {
    $response3 = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body3 -ContentType "application/json"
    Write-Host "Success:" -ForegroundColor Green
    $response3 | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}
Write-Host "`n"

# Test 4: Error case - missing exec_id
Write-Host "Test 4: Error case - missing exec_id (should return 422)" -ForegroundColor Yellow
$body4 = @{
    callback_path = "/trigger/upload_nf_files_to_s3"
} | ConvertTo-Json

try {
    $response4 = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body4 -ContentType "application/json"
    Write-Host "Unexpected success:" -ForegroundColor Yellow
    $response4 | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Expected error:" -ForegroundColor Green
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    } else {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}
Write-Host "`n"

# Test 5: Error case - invalid exec_id (non-existent)
Write-Host "Test 5: Error case - invalid exec_id (should return 422)" -ForegroundColor Yellow
$body5 = @{
    exec_id = 99999
} | ConvertTo-Json

try {
    $response5 = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body5 -ContentType "application/json"
    Write-Host "Unexpected success:" -ForegroundColor Yellow
    $response5 | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Expected error:" -ForegroundColor Green
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    } else {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}
Write-Host "`n"

Write-Host "Testing complete!" -ForegroundColor Cyan



