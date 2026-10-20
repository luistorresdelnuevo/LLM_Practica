# Abre la API en otra ventana de PowerShell, espera a que esté lista y lanza el juego.
$ErrorActionPreference = "Stop"
$scriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$scriptsDir\iniciar_api.ps1`""

Write-Host "Esperando a la API (la primera vez se crean los embeddings)..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8077/health" -TimeoutSec 2
        if ($health.assistant_ready) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Warning "La API no está lista; el juego arrancará igualmente y mostrará el error."
}
& "$scriptsDir\iniciar_juego.ps1"
