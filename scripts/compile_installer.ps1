# Compila solo l'installer Inno Setup (PyInstaller deve essere già stato eseguito)
# Uso:
#   .\scripts\compile_installer.ps1
#   .\scripts\compile_installer.ps1 -InnoDir "D:\Tools\Inno Setup 6"

param(
    [string]$InnoDir = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Iss = Join-Path $ProjectRoot "desktop\installer\setup.iss"
$DistApp = Join-Path $ProjectRoot "desktop\dist\MAC_AI_Assistant\MAC_AI_Assistant.exe"

if (-not (Test-Path $DistApp)) {
    Write-Error "Build PyInstaller mancante. Eseguire prima: python scripts\build_release.py --skip-installer"
}

Write-Host "Pulizia artefatti dist..." -ForegroundColor Cyan
& python (Join-Path $ProjectRoot "scripts\clean_dist.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$candidates = @()
if ($InnoDir) { $candidates += Join-Path $InnoDir "ISCC.exe" }
$candidates += @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($cmd in (Get-Command ISCC -ErrorAction SilentlyContinue)) { $iscc = $cmd.Source; break }
if (-not $iscc) {
    foreach ($path in $candidates) {
        if (Test-Path $path) { $iscc = $path; break }
    }
}

if (-not $iscc) {
    Write-Host "ISCC.exe non trovato. Indicare il percorso:" -ForegroundColor Yellow
    Write-Host '  .\scripts\compile_installer.ps1 -InnoDir "C:\percorso\Inno Setup 6"' -ForegroundColor Yellow
    exit 1
}

Write-Host "Compilazione installer con: $iscc" -ForegroundColor Cyan
& $iscc $Iss
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$setup = Join-Path $ProjectRoot "dist\installer\MAC_AI_Assistant_Setup.exe"
if (Test-Path $setup) {
    $size = [math]::Round((Get-Item $setup).Length / 1MB, 1)
    Write-Host "`n[OK] Installer creato: $setup ($size MB)" -ForegroundColor Green
} else {
    $alt = Get-ChildItem (Join-Path $ProjectRoot "desktop\installer\Output") -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($alt) {
        New-Item -ItemType Directory -Force -Path (Split-Path $setup) | Out-Null
        Copy-Item $alt.FullName $setup
        Write-Host "`n[OK] Installer copiato: $setup" -ForegroundColor Green
    } else {
        Write-Error "Installer non trovato dopo compilazione"
    }
}
