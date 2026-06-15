$ErrorActionPreference = "Stop"

$sdkRoot = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$cmdTools = Join-Path $sdkRoot "cmdline-tools\latest"
$sdkManager = Join-Path $cmdTools "bin\sdkmanager.bat"

New-Item -ItemType Directory -Force -Path $sdkRoot | Out-Null

if (-not (Test-Path $sdkManager)) {
    $zipPath = Join-Path $env:TEMP "commandlinetools-win.zip"
    $url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    Write-Host "Download Android command line tools..."
    Invoke-WebRequest -Uri $url -OutFile $zipPath
    $extractDir = Join-Path $env:TEMP "android-cmdline"
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractDir
    New-Item -ItemType Directory -Force -Path (Join-Path $sdkRoot "cmdline-tools\latest") | Out-Null
    Copy-Item -Path (Join-Path $extractDir "cmdline-tools\*") -Destination (Join-Path $sdkRoot "cmdline-tools\latest") -Recurse -Force
}

$env:JAVA_HOME = (Get-ChildItem "C:\Program Files\Microsoft\jdk-*" | Sort-Object Name -Descending | Select-Object -First 1).FullName
$env:ANDROID_HOME = $sdkRoot
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"

Write-Host "Install SDK packages..."
& $sdkManager --sdk_root=$sdkRoot --install "platform-tools" "platforms;android-35" "build-tools;35.0.0" | Out-Host
cmd /c "echo y| $sdkManager --sdk_root=$sdkRoot --licenses"

$localProps = Join-Path $PSScriptRoot "..\local.properties"
"sdk.dir=$($sdkRoot -replace '\\','\\')" | Set-Content -Path $localProps -Encoding ASCII
Write-Host "SDK ready at $sdkRoot"
