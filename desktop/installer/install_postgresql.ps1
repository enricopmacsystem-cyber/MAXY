# Installazione silenziosa PostgreSQL per Maxy AI (password allineata a hub.env.default).
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [string]$SuperPassword = "admin",
    [int]$Port = 5432,
    [switch]$TestOnly
)

$ErrorActionPreference = "Continue"
$logDir = Join-Path $env:APPDATA "MAC AI Assistant\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "install_postgresql.log"

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -Path $logFile -Value $line
}

function Test-PostgresPort {
    param([int]$TargetPort = 5432)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", $TargetPort)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Test-PostgresInstalled {
    if (Test-PostgresPort) {
        return $true
    }
    $services = @(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*postgres*" })
    return ($services.Count -gt 0)
}

if ($TestOnly) {
    if (Test-PostgresInstalled) { exit 0 }
    exit 1
}

Write-Log "=== Installazione PostgreSQL ==="

if (Test-PostgresInstalled) {
    Write-Log "PostgreSQL gia presente o porta $($Port) in uso - installazione non necessaria."
    & (Join-Path $PSScriptRoot "ensure_postgresql.ps1") -TimeoutSeconds 60
    exit $LASTEXITCODE
}

if (-not (Test-Path $InstallerPath)) {
    Write-Log "Installer PostgreSQL non trovato: $InstallerPath"
    exit 2
}

Write-Log "Avvio installer: $InstallerPath"
$arguments = @(
    "--mode", "unattended",
    "--unattendedmodeui", "none",
    "--superpassword", $SuperPassword,
    "--servicepassword", $SuperPassword,
    "--serverport", "$Port",
    "--install_runtimes", "0",
    "--enable_acledit", "1",
    "--create_shortcuts", "0"
)

$proc = Start-Process -FilePath $InstallerPath -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
Write-Log "Exit code installer PostgreSQL: $($proc.ExitCode)"

if ($proc.ExitCode -ne 0) {
    exit $proc.ExitCode
}

& (Join-Path $PSScriptRoot "ensure_postgresql.ps1") -TimeoutSeconds 120
if ($LASTEXITCODE -ne 0) {
    Write-Log "PostgreSQL installato ma porta $($Port) non raggiungibile."
    exit 3
}

Write-Log "PostgreSQL installato e raggiungibile su 127.0.0.1:$($Port)"
exit 0
