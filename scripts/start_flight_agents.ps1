# Start agents required for flight plan processing
Write-Host "========================================"
Write-Host "Starting Flight Plan Processing Agents"
Write-Host "======================================`n"

$agentsDir = Join-Path $PSScriptRoot ".." "agents"

# Start state_logger (CRITICAL - stores events in MongoDB)
Write-Host "[1] Starting state_logger.py..."
Start-Process python -ArgumentList "$agentsDir\state_logger.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start trajectory_insight_agent (CRITICAL - processes flight.parsed events)
Write-Host "[2] Starting trajectory_insight_agent.py..."
Start-Process python -ArgumentList "$agentsDir\trajectory_insight_agent.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start coordinator_agent (Optional but recommended)
Write-Host "[3] Starting coordinator_agent.py..."
Start-Process python -ArgumentList "$agentsDir\coordinator_agent.py" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host "`nAll agents started!`n"
Write-Host "IMPORTANT:"
Write-Host "  - state_logger.py stores ALL events in MongoDB"
Write-Host "  - trajectory_insight_agent.py processes flight.parsed events"
Write-Host "  - coordinator_agent.py coordinates recovery plans`n"
Write-Host "Now upload a flight plan through the dashboard and events should appear!`n"

