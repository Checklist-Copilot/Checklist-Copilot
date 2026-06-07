# dev.ps1 — convenience launcher for local development.
#
# Spawns two new PowerShell windows: one running the FastAPI backend on
# http://localhost:8000, one running the Vite frontend on http://localhost:5173.
# Each child window survives its own Ctrl+C; close them when you're done.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\dev.ps1
#   # or, with execution policy already set to RemoteSigned:
#   .\dev.ps1

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir  = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend\checklist-copilot-frontend'

if (-not (Test-Path $backendDir)) {
    Write-Error "backend directory not found at $backendDir"
}
if (-not (Test-Path $frontendDir)) {
    Write-Error "frontend directory not found at $frontendDir"
}

# Run the backend in its own PowerShell window. -NoExit keeps the window open
# after the process ends so you can read any error message.
Write-Host '> Starting backend (uvicorn) in a new window on :8000...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location -LiteralPath '$backendDir'; python -m uvicorn app.main:app --reload --port 8000"
)

Write-Host '> Starting frontend (vite) in a new window on :5173...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location -LiteralPath '$frontendDir'; npm run dev"
)

Write-Host ''
Write-Host 'Both servers are starting up in separate windows.'
Write-Host '  - Backend  Swagger UI:  http://localhost:8000/docs'
Write-Host '  - Frontend (Vite dev):  http://localhost:5173'
Write-Host ''
Write-Host 'Close the spawned windows when you are done.'
