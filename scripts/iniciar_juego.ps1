$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectDir

$env:PYTHONPATH = (Join-Path $projectDir "src")
& ".venv\Scripts\python.exe" "game\main.py"
