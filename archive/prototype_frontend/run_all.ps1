# SEABeacon Demo 2 — launch all backends + frontend (Windows / PowerShell)
#
# Starts the three AI daemons each in their own window, then the Vite dev server
# in this window. Assumes each backend's .env and frontend/.env are configured
# and dependencies are installed (see README.md).
#
# Usage:  ./run_all.ps1

$ErrorActionPreference = "Stop"
$demo2  = $PSScriptRoot
$phase1 = Split-Path $demo2 -Parent

function Start-Daemon($title, $dir, $cmd) {
    if (-not (Test-Path $dir)) {
        Write-Warning "Skipping $title — directory not found: $dir"
        return
    }
    Write-Host "Starting $title ..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle='$title'; Set-Location '$dir'; $cmd"
    )
}

# ── Backends (each in its own window) ─────────────────────────────────────────
Start-Daemon "SEABeacon AI-1 Flood (LSTM)"  (Join-Path $phase1 "lstm_model")            "python main.py"
Start-Daemon "SEABeacon AI-2 Typhoon (XGB)" (Join-Path $phase1 "xgboost_forecast\automation") "python daemon.py"
Start-Daemon "SEABeacon AI-3 Social (NLP)"  (Join-Path $phase1 "nlp_analysis")          "python main.py"

# ── Frontend (this window) ────────────────────────────────────────────────────
Write-Host "Starting frontend (Vite dev server) ..." -ForegroundColor Green
Set-Location (Join-Path $demo2 "frontend")
npm run dev
