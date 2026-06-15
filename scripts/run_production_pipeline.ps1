# Pipeline di produzione Maxy AI (PowerShell)
# Uso:
#   .\scripts\run_production_pipeline.ps1
#   .\scripts\run_production_pipeline.ps1 -Phase "preflight,security"
#   .\scripts\run_production_pipeline.ps1 -Phase release -RequireAgentApproval

param(
    [string]$Phase = "all",
    [switch]$SkipBuild,
    [switch]$SkipInstaller,
    [switch]$RequireAgentApproval,
    [switch]$NoAgentPrompts
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$args = @("scripts/run_production_pipeline.py", "--phase", $Phase)
if ($SkipBuild) { $args += "--skip-build" }
if ($SkipInstaller) { $args += "--skip-installer" }
if ($RequireAgentApproval) { $args += "--require-agent-approval" }
if ($NoAgentPrompts) { $args += "--no-agent-prompts" }

Write-Host "=== Maxy AI - Production Pipeline ===" -ForegroundColor Cyan
& python @args
exit $LASTEXITCODE
