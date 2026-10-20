$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectDir

$env:PYTHONPATH = (Join-Path $projectDir "src")
& ".venv\Scripts\python.exe" -m uvicorn tenerife_assistant.api:app --host 127.0.0.1 --port 8077 --reload
