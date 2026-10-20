param(
  [string]$BaseUrl = 'https://zuoyou-space-libretv.onrender.com',
  [Parameter(Mandatory=$true)][string]$CredentialFile
)
$ErrorActionPreference = 'Stop'
if ($BaseUrl -ne 'https://zuoyou-space-libretv.onrender.com') {
  throw 'Production smoke credentials may only be sent to the confirmed LibreTV service.'
}
$passwordLine = [IO.File]::ReadAllLines((Resolve-Path -LiteralPath $CredentialFile).Path) | Where-Object { $_.StartsWith('PASSWORD=') } | Select-Object -First 1
if (-not $passwordLine) { throw 'PASSWORD not found in local private configuration.' }
$password = $passwordLine.Substring(9)
$health = Invoke-RestMethod -Uri ($BaseUrl + '/healthz') -TimeoutSec 60
if ($health.status -ne 'ok') { throw 'Health check failed.' }
Write-Output 'Public health: passed'
try {
  Invoke-WebRequest -Method Post -Uri ($BaseUrl + '/api/search') -ContentType 'application/json' -Body '{"wd":"test","sources":[]}' -TimeoutSec 30 | Out-Null
  throw 'Unauthenticated search unexpectedly allowed.'
} catch {
  if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
}
Write-Output 'Unauthenticated search: 401'
$loginBody = @{ password=$password } | ConvertTo-Json -Compress
$login = Invoke-WebRequest -Method Post -Uri ($BaseUrl + '/api/auth') -ContentType 'application/json' -Body $loginBody -SessionVariable tvSession -MaximumRedirection 0 -TimeoutSec 30
$flags = [string]$login.Headers['Set-Cookie']
if ($flags -notmatch 'HttpOnly' -or $flags -notmatch 'Secure' -or $flags -notmatch 'SameSite=Lax') { throw 'Secure session cookie flags missing.' }
$status = Invoke-RestMethod -Uri ($BaseUrl + '/api/status') -WebSession $tvSession -TimeoutSec 30
if (-not $status.verified -or -not $status.passwordRequired -or $status.localAutoLogin) { throw 'Production session verification failed.' }
Write-Output 'Password login and Secure/HttpOnly session: passed'
try {
  Invoke-WebRequest -Uri ($BaseUrl + '/api/proxy?url=http%3A%2F%2F127.0.0.1%2Ftest') -WebSession $tvSession -TimeoutSec 30 | Out-Null
  throw 'Private proxy target unexpectedly allowed.'
} catch {
  if ($_.Exception.Response.StatusCode.value__ -notin @(400,403)) { throw }
}
Write-Output 'Private proxy target: blocked'
$broken = Invoke-RestMethod -Uri ($BaseUrl + '/api/auth') -Headers @{ Cookie='ltv_session=%ZZ' } -TimeoutSec 30
if ($broken.verified) { throw 'Malformed cookie accepted.' }
Write-Output 'Malformed cookie: rejected'
foreach ($page in @('/', '/live', '/watch', '/about')) {
  $response = Invoke-WebRequest -Uri ($BaseUrl + $page) -TimeoutSec 30
  if ($response.StatusCode -ne 200) { throw "Page unavailable: $page" }
}
Write-Output 'Home, live, watch and about pages: HTTP 200'
Invoke-RestMethod -Method Delete -Uri ($BaseUrl + '/api/auth') -WebSession $tvSession -TimeoutSec 30 | Out-Null
$loggedOut = Invoke-RestMethod -Uri ($BaseUrl + '/api/auth') -WebSession $tvSession -TimeoutSec 30
if ($loggedOut.verified) { throw 'Logout failed.' }
Write-Output 'Logout: passed'
# No password, cookie, media URL or viewing data is printed or saved.
