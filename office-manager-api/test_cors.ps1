# Test CORS headers
$headers = @{
    Origin = 'http://localhost:3000'
    'Content-Type' = 'application/x-www-form-urlencoded'
}

try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -Headers $headers -Body 'username=test1@test.com&password=Test1234' -UseBasicParsing

    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host ""
    Write-Host "Response Headers:"
    $response.Headers.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key): $($_.Value)" }
    Write-Host ""
    Write-Host "Response Body:"
    $response.Content
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "Response: $($reader.ReadToEnd())"
    }
}
