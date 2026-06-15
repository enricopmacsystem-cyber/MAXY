# MAC AI Assistant - Build release Windows (PowerShell)
# Uso: .\scripts\build_release.ps1
#      .\scripts\build_release.ps1 -Clean -SkipInstaller

param(
    [switch]$Clean,
    [switch]$SkipInstaller,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== MAC AI Assistant - Build Release Windows ===" -ForegroundColor Cyan

# Verifica Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python non trovato nel PATH"
}

# Opzionale: VC++ Redistributable per installer
$VcRedist = Join-Path $ProjectRoot "desktop\installer\redist\VC_redist.x64.exe"
if (-not (Test-Path $VcRedist)) {
    Write-Host "[INFO] VC_redist.x64.exe non presente in desktop\installer\redist\" -ForegroundColor Yellow
    Write-Host "       Scaricare da: https://aka.ms/vs/17/release/vc_redist.x64.exe" -ForegroundColor Yellow
    Write-Host "       L'installer funzionerà comunque senza prerequisito VC++ integrato." -ForegroundColor Yellow
}

$args = @("scripts/build_release.py")
if ($Clean) { $args += "--clean" }
if ($SkipInstaller) { $args += "--skip-installer" }
if ($SkipDeps) { $args += "--skip-deps" }

& python @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nBuild completata." -ForegroundColor Green
Write-Host "Installer: dist\installer\MAC_AI_Assistant_Setup.exe" -ForegroundColor Green
