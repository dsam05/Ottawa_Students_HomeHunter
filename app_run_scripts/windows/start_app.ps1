$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..\..")
Set-Location $RootDir

$Port = if ($env:PORT) { [int]$env:PORT } else { 5001 }
$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

$Existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "HomeHunter is already running on http://127.0.0.1:$Port/"
    Write-Host "Use app_run_scripts\windows\stop_app.ps1 first if you want to restart it."
    exit 0
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating local Python environment in .venv..."
    & $PythonBin -m venv $VenvDir
}

& $VenvPython -c "import duckdb, flask, flask_cors" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies into .venv..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
}

Write-Host "Starting HomeHunter at http://127.0.0.1:$Port/"
& $VenvPython src/main/backend/app.py
