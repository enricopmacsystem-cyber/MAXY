# Riavvia il servizio locale MAC AI Assistant (Integration Hub)
$port = 8000
$hubEnv = Join-Path $env:APPDATA "MAC AI Assistant\hub.env"

Write-Host "Arresto servizio sulla porta $port..."
try {
    $procId = (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1).OwningProcess
    if ($procId) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
} catch {}

$hubExe = @(
    "${env:LOCALAPPDATA}\Programs\Maxy 2.0 - daisy\hub\MAC_AI_Hub.exe",
    "${env:LOCALAPPDATA}\Programs\MAC AI Assistant\hub\MAC_AI_Hub.exe",
    "${env:ProgramFiles}\Maxy 2.0 - daisy\hub\MAC_AI_Hub.exe",
    "${env:ProgramFiles}\MAC AI Assistant\hub\MAC_AI_Hub.exe",
    (Join-Path $PSScriptRoot "..\dist\MAC_AI_Hub\MAC_AI_Hub.exe"),
    (Join-Path $PSScriptRoot "..\desktop\dist\MAC_AI_Hub\MAC_AI_Hub.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $hubExe) {
    Write-Host "MAC_AI_Hub.exe non trovato. Reinstallare MAC AI Assistant."
    exit 1
}

Write-Host "Avvio: $hubExe"
$env:MAC_AI_HUB_ENV = $hubEnv
$hubDir = Split-Path -Parent $hubExe
Start-Process -FilePath $hubExe -WorkingDirectory $hubDir -WindowStyle Hidden
Start-Sleep -Seconds 6

try {
    $health = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 5
    Write-Host "Servizio OK - EasyOne:" $health.easyone_api_url
} catch {
    Write-Host "Servizio non risponde. Verificare PostgreSQL."
    exit 1
}
