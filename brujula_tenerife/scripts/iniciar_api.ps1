# Inicia la API local de La brújula de Tenerife en http://127.0.0.1:8077
# La clave se lee del .env del proyecto; este script no contiene secretos.
$ErrorActionPreference = "Stop"
$brujulaDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path (Split-Path -Parent $brujulaDir) ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "No se encontró .venv. Ejecuta primero scripts\setup_windows.ps1 en la raíz del proyecto."
}
Set-Location $brujulaDir
& $python -m uvicorn backend.api:app --host 127.0.0.1 --port 8077
