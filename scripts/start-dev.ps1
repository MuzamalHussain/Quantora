param(
    [ValidateSet('Start','Stop','Status','StartCollector','InitializeSecrets','ReadMail','BootstrapAdmin')]
    [string]$Action = 'Start'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cache = Join-Path $root '.cache'
$statePath = Join-Path $cache 'dev-runtime.json'
$keyPath = Join-Path $cache 'dev-custody-key.dpapi'
$mailPath = Join-Path $cache 'local-mail'
$logDir = Join-Path $cache 'dev-logs'
$python = Join-Path $root '.venv\Scripts\python.exe'
$core = Join-Path $root 'services\trading-core\target\debug\quantora-core.exe'
$vite = Join-Path $root 'node_modules\vite\bin\vite.js'
$webDir = Join-Path $root 'apps\web'
$apiDir = Join-Path $root 'services\control-api'

function Test-Port([int]$port) {
    $tcp = [Net.Sockets.TcpClient]::new()
    try { $tcp.Connect('127.0.0.1', $port); return $true }
    catch { return $false }
    finally { $tcp.Dispose() }
}

function Wait-Http([string]$url, [int]$seconds = 20) {
    $until = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $until) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    throw "Readiness failed for $url; inspect .cache/dev-logs."
}

function Load-Secrets {
    if ($env:QUANTORA_CUSTODY_KEYS -and $env:QUANTORA_ACTIVE_KEY) {
        $env:QUANTORA_LOCAL_MAIL_DIR = $mailPath
        return
    }
    if (-not (Test-Path -LiteralPath $keyPath)) {
        throw 'No local custody key. Run scripts/start-dev.ps1 -Action InitializeSecrets once, or supply existing QUANTORA_CUSTODY_KEYS and QUANTORA_ACTIVE_KEY securely in this shell.'
    }
    $protected = Get-Content -LiteralPath $keyPath -Raw
    $secure = ConvertTo-SecureString ($protected.Trim())
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $encoded = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    $env:QUANTORA_CUSTODY_KEYS = @{ 'local-v1' = $encoded } | ConvertTo-Json -Compress
    $env:QUANTORA_ACTIVE_KEY = 'local-v1'
    $env:QUANTORA_LOCAL_MAIL_DIR = $mailPath
}

function Read-State {
    if (Test-Path -LiteralPath $statePath) {
        return Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    }
    return $null
}

function Get-OwnedProcess($item) {
    if (-not $item) { return $null }
    $process = Get-Process -Id $item.pid -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if ($process.ProcessName -ne $item.name) { return $null }
    if ($process.StartTime.ToUniversalTime().ToString('o') -ne $item.started) { return $null }
    return $process
}

if ($Action -eq 'InitializeSecrets') {
    if ((Test-Path -LiteralPath $keyPath) -or $env:QUANTORA_CUSTODY_KEYS) {
        throw 'A custody key is already configured; existing key material was not changed.'
    }
    & $python (Join-Path $root 'scripts\local_key_guard.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Cannot safely create a new key: encrypted data/mail may exist or MongoDB is unavailable. Restore the original key instead.'
    }
    New-Item -ItemType Directory -Force -Path $cache, $mailPath | Out-Null
    $bytes = [byte[]]::new(32)
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    try {
        $encoded = [Convert]::ToBase64String($bytes)
        ConvertTo-SecureString -String $encoded -AsPlainText -Force |
            ConvertFrom-SecureString | Set-Content -LiteralPath $keyPath -NoNewline
    } finally { [Array]::Clear($bytes, 0, $bytes.Length) }
    Write-Host 'Created a current-Windows-user-protected local custody key. Back up this file securely before storing credentials.'
    return
}

if ($Action -eq 'ReadMail' -or $Action -eq 'BootstrapAdmin') {
    Load-Secrets
    $operation = if ($Action -eq 'ReadMail') { 'read-local-mail' } else { 'bootstrap-admin' }
    Push-Location $apiDir
    try { & $python -m quantora_api.manage $operation; exit $LASTEXITCODE }
    finally { Pop-Location }
}

if ($Action -eq 'Status') {
    $state = Read-State
    foreach ($port in @(8101,8000,5173,27117,6381)) {
        Write-Host "127.0.0.1:${port}: $(if (Test-Port $port) { 'listening' } else { 'down' })"
    }
    if ($state) {
        foreach ($role in @('core','api','web','collector')) {
            $items = @($state.processes | Where-Object { $_.role -eq $role })
            if ($items.Count -eq 0) { continue }
            $running = @($items | Where-Object { Get-OwnedProcess $_ }).Count -gt 0
            Write-Host "${role}: $(if ($running) { 'owned and running' } else { 'not running' })"
        }
    }
    return
}

if ($Action -eq 'Stop') {
    $state = Read-State
    if (-not $state) { Write-Host 'No launcher-owned runtime recorded.'; return }
    for ($i = @($state.processes).Count - 1; $i -ge 0; $i--) {
        $item = @($state.processes)[$i]
        $process = Get-OwnedProcess $item
        if ($process) { Stop-Process -Id $process.Id; Write-Host "Stopped owned $($item.role)." }
    }
    Remove-Item -LiteralPath $statePath
    return
}

if ($Action -eq 'StartCollector') {
    $state = Read-State
    if (-not $state -or -not (Test-Port 8000)) { throw 'Start the local API first.' }
    if (@($state.processes | Where-Object { $_.role -eq 'collector' -and (Get-OwnedProcess $_) }).Count -gt 0) {
        Write-Host 'The launcher-owned collector is already running.'
        return
    }
    $owned = [Collections.Generic.List[object]]::new()
    foreach ($item in $state.processes) { $owned.Add($item) }
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $out = Join-Path $logDir 'collector.stdout.log'
    $err = Join-Path $logDir 'collector.stderr.log'
    $process = Start-Process -FilePath $python -ArgumentList @('scripts/phase04_collector.py','--database','quantora_app','--symbol','BTCUSDT','--continuous','--seconds','60') -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $owned.Add([pscustomobject]@{role='collector';pid=$process.Id;name=$process.ProcessName;started=$process.StartTime.ToUniversalTime().ToString('o')})
    [pscustomobject]@{processes=$owned.ToArray();started_at=$state.started_at} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath
    Start-Sleep -Seconds 3
    if (Get-OwnedProcess $owned[$owned.Count - 1]) { Write-Host 'Public collector running.' }
    else { Write-Warning 'Public collector stopped. Check .cache/dev-logs/collector.stderr.log; public feed may be provider-blocked.' }
    return
}

$previous = Read-State
if ($previous -and (Test-Port 8101) -and (Test-Port 8000) -and (Test-Port 5173)) {
    $services = @($previous.processes | Where-Object { $_.role -in @('core','api','web') -and (Get-OwnedProcess $_) })
    if ($services.Count -eq 3) {
        Write-Host 'Quantora is already running at http://127.0.0.1:5173; no duplicate services started.'
        return
    }
}

if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $core) -or -not (Test-Path -LiteralPath $vite)) {
    throw 'Existing Python, Rust core or Vite runtime is missing; inspect installed workspace dependencies.'
}
foreach ($port in @(8101,8000,5173)) {
    if (Test-Port $port) { throw "Port $port is already occupied. Inspect the existing service; no duplicate was started." }
}
foreach ($port in @(27117,6381)) {
    if (-not (Test-Port $port)) { throw "Dependency port $port is down. Start the existing MongoDB/Redis containers first." }
}
Load-Secrets
New-Item -ItemType Directory -Force -Path $cache, $mailPath, $logDir | Out-Null

Push-Location $apiDir
try {
    & $python -m quantora_api.manage migrate
    if ($LASTEXITCODE -ne 0) { throw 'Migration compatibility check failed.' }
} finally { Pop-Location }

$owned = [Collections.Generic.List[object]]::new()
function Start-Owned([string]$role, [string]$file, [string[]]$arguments, [string]$workingDirectory) {
    $out = Join-Path $logDir "$role.stdout.log"
    $err = Join-Path $logDir "$role.stderr.log"
    $start = @{FilePath=$file; WorkingDirectory=$workingDirectory; WindowStyle='Hidden'; PassThru=$true; RedirectStandardOutput=$out; RedirectStandardError=$err}
    if ($arguments.Count -gt 0) { $start.ArgumentList = $arguments }
    $process = Start-Process @start
    $owned.Add([pscustomobject]@{role=$role; pid=$process.Id; name=$process.ProcessName; started=$process.StartTime.ToUniversalTime().ToString('o')})
}

try {
    Start-Owned 'core' $core @() $root
    Wait-Http 'http://127.0.0.1:8101/health/live'
    Start-Owned 'api' $python @('-m','quantora_api') $apiDir
    Wait-Http 'http://127.0.0.1:8000/health/ready'
    Start-Owned 'web' (Get-Command node.exe).Source @($vite,'--host','127.0.0.1','--port','5173','--strictPort') $webDir
    Wait-Http 'http://127.0.0.1:5173/'
    Start-Owned 'collector' $python @('scripts/phase04_collector.py','--database','quantora_app','--symbol','BTCUSDT','--continuous','--seconds','60') $root
    [pscustomobject]@{processes=$owned.ToArray(); started_at=(Get-Date).ToUniversalTime().ToString('o')} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath
    Start-Sleep -Seconds 3
    if (Get-OwnedProcess $owned[$owned.Count - 1]) {
        Write-Host 'Quantora ready at http://127.0.0.1:5173; public collector running.'
    } else {
        Write-Warning 'API and UI are ready at http://127.0.0.1:5173, but the public collector stopped. Inspect .cache/dev-logs/collector.stderr.log. Stored/fixture views remain distinct.'
    }
} catch {
    foreach ($item in $owned) { $process = Get-OwnedProcess $item; if ($process) { Stop-Process -Id $process.Id } }
    throw
}
