# Test full login flow
$login = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -ContentType 'application/x-www-form-urlencoded' -Body 'username=test1@test.com&password=Test1234'

Write-Host "Login response:"
$login | ConvertTo-Json

Write-Host "`nFetching /auth/me..."
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$me = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/me' -Headers $headers

Write-Host "User data:"
$me | ConvertTo-Json
