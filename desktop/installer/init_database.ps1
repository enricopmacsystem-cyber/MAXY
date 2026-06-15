# Preparazione database locale — non blocca l'installer se PostgreSQL non è pronto.
param(
    [Parameter(Mandatory = $true)]
    [string]$HubExe
)

$ErrorActionPreference = "Continue"
$appData = Join-Path $env:APPDATA "MAC AI Assistant"
$logDir = Join-Path $appData "logs"
$pendingFlag = Join-Path $appData "db_init_pending.flag"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "install_database.log"

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -Path $logFile -Value $line
}

Write-Log "=== Inizio preparazione database ==="

$ensureScript = Join-Path $PSScriptRoot "ensure_postgresql.ps1"
if (Test-Path $ensureScript) {
    & $ensureScript -TimeoutSeconds 45
    $pgReady = ($LASTEXITCODE -eq 0)
}
else {
    $pgReady = $false
    Write-Log "Script ensure_postgresql.ps1 non trovato"
}

if (-not $pgReady) {
    Write-Log "PostgreSQL non disponibile: init-db rimandato al primo avvio Maxy AI"
    Set-Content -Path $pendingFlag -Value "pending" -Encoding UTF8
    exit 0
}

if (-not (Test-Path $HubExe)) {
    Write-Log "Hub non trovato: $HubExe"
    Set-Content -Path $pendingFlag -Value "pending" -Encoding UTF8
    exit 0
}

Write-Log "Esecuzione: $HubExe --init-db"
$proc = Start-Process -FilePath $HubExe -ArgumentList "--init-db" -Wait -PassThru -WindowStyle Hidden
Write-Log "Exit code init-db: $($proc.ExitCode)"

if ($proc.ExitCode -ne 0) {
    Set-Content -Path $pendingFlag -Value "pending" -Encoding UTF8
    Write-Log "Init-db fallito: vedi hub.log e install_database.log"
    exit 0
}

if (Test-Path $pendingFlag) {
    Remove-Item $pendingFlag -Force
}
Write-Log "Database inizializzato con successo"
exit 0
