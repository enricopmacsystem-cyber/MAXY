# Avvia il servizio PostgreSQL locale (se installato) e attende la porta 5432.
param(
    [int]$TimeoutSeconds = 45
)

$ErrorActionPreference = "SilentlyContinue"
$logDir = Join-Path $env:APPDATA "MAC AI Assistant\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "install_postgresql.log"

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -Path $logFile -Value $line
}

Write-Log "Verifica servizio PostgreSQL..."

$services = @(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*postgres*" })
if ($services.Count -eq 0) {
    Write-Log "Nessun servizio PostgreSQL trovato su questo PC."
    exit 1
}

foreach ($svc in $services) {
    if ($svc.Status -ne "Running") {
        try {
            Start-Service -Name $svc.Name
            Write-Log "Avviato servizio $($svc.Name)"
        }
        catch {
            Write-Log "Impossibile avviare $($svc.Name): $($_.Exception.Message)"
        }
    }
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", 5432)
        $client.Close()
        Write-Log "PostgreSQL raggiungibile su 127.0.0.1:5432"
        exit 0
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

Write-Log "Timeout: PostgreSQL non raggiungibile sulla porta 5432"
exit 1
