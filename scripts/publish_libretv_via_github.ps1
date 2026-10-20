param(
  [string]$ExpectedBase = '6f537b3463574bb921341e68d523fec8695b4556',
  [string]$GitHubCli = 'D:\tool\GitHubCLI\bin\gh.exe'
)
$ErrorActionPreference = 'Stop'
$releaseRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path.Replace('\', '/')
function Read-Git([string[]]$GitArgs) {
  $result = & git -c "safe.directory=$releaseRoot" -C $releaseRoot @GitArgs
  if ($LASTEXITCODE -ne 0) { throw 'Git read failed' }
  return $result
}
function Call-GitHub([string]$Endpoint, $Payload = $null, [string]$Method = 'GET') {
  if ($null -eq $Payload) {
    $result = & $GitHubCli api $Endpoint
  } else {
    $result = ($Payload | ConvertTo-Json -Depth 12 -Compress) | & $GitHubCli api --method $Method $Endpoint --input -
  }
  if ($LASTEXITCODE -ne 0) { throw "GitHub request failed: $Endpoint" }
  return ($result | ConvertFrom-Json)
}
$repo = 'repos/ZuoyouAn/carbon-eye-release'
$remote = Call-GitHub "$repo/git/ref/heads/main"
if ($remote.object.sha -ne $ExpectedBase) { throw 'Remote main changed; do not overwrite it.' }
$localBase = Read-Git @('rev-parse', 'HEAD^')
if ($localBase -ne $ExpectedBase) { throw 'Publish exactly one isolated commit based on expected main.' }
$changes = @(Read-Git @('diff', '--name-only', $ExpectedBase, 'HEAD'))
$allowed = @('.gitignore', 'frontend/src/App.vue', 'frontend/src/router/index.js', 'frontend/src/views/HomeView.vue', 'frontend/src/views/ProjectsView.vue', 'frontend/src/views/LibreTvView.vue', 'scripts/check_libretv_browser.py', 'scripts/publish_libretv_via_github.ps1', 'docs/LIBRETV.md')
$entries = @()
foreach ($relative in $changes) {
  if (-not ($relative.StartsWith('apps/libretv/') -or $allowed -contains $relative)) { throw "Out-of-scope file: $relative" }
  if ($relative -match '(^|/)(node_modules|\.next|\.env\.local)(/|$)' -or ($relative -match '(^|/)\.env' -and $relative -ne 'apps/libretv/.env.example')) { throw 'Private or generated files cannot be published.' }
  $absolute = Join-Path $releaseRoot $relative
  if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) { throw 'This helper does not publish deletions.' }
  if ($relative -match '\.(png|ico)$') {
    $blob = Call-GitHub "$repo/git/blobs" @{ content=[Convert]::ToBase64String([IO.File]::ReadAllBytes($absolute)); encoding='base64' } 'POST'
    $entries += @{ path=$relative; mode='100644'; type='blob'; sha=$blob.sha }
  } else {
    $textContent = (Read-Git @('show', "HEAD:$relative")) -join "`n"
    $entries += @{ path=$relative; mode='100644'; type='blob'; content=($textContent + "`n") }
  }
}
$baseCommit = Call-GitHub "$repo/git/commits/$ExpectedBase"
$tree = Call-GitHub "$repo/git/trees" @{ base_tree=$baseCommit.tree.sha; tree=$entries } 'POST'
$commit = Call-GitHub "$repo/git/commits" @{ message='feat: integrate independent LibreTV cinema with Space'; tree=$tree.sha; parents=@($ExpectedBase) } 'POST'
$latest = Call-GitHub "$repo/git/ref/heads/main"
if ($latest.object.sha -ne $ExpectedBase) { throw 'Remote changed while uploading; main not updated.' }
$null = Call-GitHub "$repo/git/refs/heads/main" @{ sha=$commit.sha; force=$false } 'PATCH'
Write-Output ('Published commit: ' + $commit.sha)
