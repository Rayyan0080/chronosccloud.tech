# Start all agent services in separate PowerShell windows
# This script opens each service in its own window so you can see logs separately

Write-Host "Starting Chronos Agent Services..." -ForegroundColor Green
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot

# Start State Logger
Write-Host "Starting State Logger..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; python agents/state_logger.py"

Start-Sleep -Seconds 2

# Start Autonomy Router
Write-Host "Starting Autonomy Router..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; python agents/autonomy_router.py"

Start-Sleep -Seconds 2

# Start Solana Audit Logger
Write-Host "Starting Solana Audit Logger..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; python agents/solana_audit_logger.py"

Write-Host ""
Write-Host "All services started in separate windows!" -ForegroundColor Green
Write-Host "Close the windows or press Ctrl+C in each to stop them." -ForegroundColor Cyan

