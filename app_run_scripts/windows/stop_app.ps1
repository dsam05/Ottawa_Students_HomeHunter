$ErrorActionPreference = "Stop"

$Port = if ($env:PORT) { [int]$env:PORT } else { 5001 }
$Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $Connections) {
    Write-Host "No app process is listening on port $Port."
    exit 0
}

$ProcessIds = $Connections | Select-Object -ExpandProperty OwningProcess -Unique
Write-Host "Stopping app process(es) on port ${Port}: $($ProcessIds -join ', ')"

foreach ($ProcessId in $ProcessIds) {
    Stop-Process -Id $ProcessId -Force
}

Write-Host "Stopped app on port $Port."
