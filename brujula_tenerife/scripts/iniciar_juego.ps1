# Inicia el videojuego. Necesita la API en marcha para que los guías respondan,
# pero el juego también arranca y funciona sin ella.
$ErrorActionPreference = "Stop"
$brujulaDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path (Split-Path -Parent $brujulaDir) ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "No se encontró .venv. Ejecuta primero scripts\setup_windows.ps1 en la raíz del proyecto."
}
Set-Location $brujulaDir
& $python -m game.main
