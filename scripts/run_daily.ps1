param([int]$Limit = 24)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    & (Join-Path $projectRoot '.venv/Scripts/python.exe') -m qaf.cli run --limit $Limit
    $runExit = $LASTEXITCODE
} finally { Pop-Location }
exit $runExit
