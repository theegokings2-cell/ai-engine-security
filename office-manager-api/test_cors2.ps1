# Test CORS with different origins
Write-Host "=== Test 1: Origin = http://localhost:3000 (should match) ==="
$headers = @{
    Origin = 'http://localhost:3000'
    'Content-Type' = 'application/x-www-form-urlencoded'
}
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -Headers $headers -Body 'username=test1@test.com&password=Test1234' -UseBasicParsing
    Write-Host "ACAO Header: $($response.Headers['access-control-allow-origin'])"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "=== Test 2: Origin = http://evil.com (should NOT match) ==="
$headers2 = @{
    Origin = 'http://evil.com'
    'Content-Type' = 'application/x-www-form-urlencoded'
}
try {
    $response2 = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -Headers $headers2 -Body 'username=test1@test.com&password=Test1234' -UseBasicParsing
    Write-Host "ACAO Header: $($response2.Headers['access-control-allow-origin'])"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "=== Test 3: No Origin header ==="
$headers3 = @{
    'Content-Type' = 'application/x-www-form-urlencoded'
}
try {
    $response3 = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -Headers $headers3 -Body 'username=test1@test.com&password=Test1234' -UseBasicParsing
    Write-Host "ACAO Header: $($response3.Headers['access-control-allow-origin'])"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}
