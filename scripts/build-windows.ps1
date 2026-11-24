<#
.SYNOPSIS
Build spkup from this checkout and install it for the current user.

.DESCRIPTION
Creates .venv if needed, builds with PyInstaller, validates the bundled CUDA/cuDNN
DLLs, then installs to %LOCALAPPDATA%\Programs\spkup and adds a Start Menu shortcut.

Usage:  powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
Env:    SPKUP_INSTALL_DIR  install folder (default %LOCALAPPDATA%\Programs\spkup)
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Checked {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $File $($Arguments -join ' ')" }
}

$installDir = if ($env:SPKUP_INSTALL_DIR) { $env:SPKUP_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA 'Programs\spkup' }

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host '==> Creating .venv'
    Invoke-Checked 'py' @('-3.12', '-m', 'venv', '.venv')
}
$py = (Resolve-Path '.venv\Scripts\python.exe').Path

Write-Host '==> Installing build dependencies'
Invoke-Checked $py @('-m', 'pip', 'install', '--quiet', '--upgrade', 'pip')
Invoke-Checked $py @('-m', 'pip', 'install', '--quiet', '-e', '.[build,gpu]')

Write-Host '==> Building dist\spkup'
foreach ($dir in 'build', 'dist') {
    if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
}
Invoke-Checked $py @('-m', 'PyInstaller', '--clean', '--noconfirm', '--log-level', 'WARN', 'spkup.spec')
Invoke-Checked $py @('-m', 'spkup.packaging_validation', 'dist\spkup')

$running = Get-Process -Name 'spkup' -ErrorAction SilentlyContinue
if ($running) {
    Write-Host '==> Stopping the running spkup'
    $running | Stop-Process -Force
    $running | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
}

Write-Host "==> Installing to $installDir"
if (Test-Path $installDir) {
    # Only replace a folder that holds a previous spkup install, never an arbitrary path.
    $isSpkupDir = Test-Path (Join-Path $installDir 'spkup.exe')
    $isEmpty = -not (Get-ChildItem $installDir -Force | Select-Object -First 1)
    if (-not ($isSpkupDir -or $isEmpty)) {
        throw "$installDir exists and is not an spkup install; set SPKUP_INSTALL_DIR to another folder"
    }
    Remove-Item $installDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path $installDir -Parent) | Out-Null
Copy-Item 'dist\spkup' $installDir -Recurse

$exe = Join-Path $installDir 'spkup.exe'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'spkup.lnk'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $installDir
$shortcut.Save()

$env:PYTHONPATH = 'src'
$version = & $py -c 'from spkup import __version__; print(__version__)'
Write-Host ''
Write-Host "spkup $version installed at $exe"
Write-Host "Start Menu shortcut: $shortcutPath"
