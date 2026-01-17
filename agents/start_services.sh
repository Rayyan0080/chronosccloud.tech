#!/bin/bash
# Start all agent services in separate terminal windows
# For Linux/Mac/Git Bash

echo "Starting Chronos Agent Services..."
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Start State Logger
echo "Starting State Logger..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT' && python agents/state_logger.py; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT' && python agents/state_logger.py; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python agents/state_logger.py\"" 2>/dev/null || \
echo "Could not open new terminal. Run manually: python agents/state_logger.py"

sleep 2

# Start Autonomy Router
echo "Starting Autonomy Router..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT' && python agents/autonomy_router.py; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT' && python agents/autonomy_router.py; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python agents/autonomy_router.py\"" 2>/dev/null || \
echo "Could not open new terminal. Run manually: python agents/autonomy_router.py"

sleep 2

# Start Solana Audit Logger
echo "Starting Solana Audit Logger..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT' && python agents/solana_audit_logger.py; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT' && python agents/solana_audit_logger.py; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python agents/solana_audit_logger.py\"" 2>/dev/null || \
echo "Could not open new terminal. Run manually: python agents/solana_audit_logger.py"

echo ""
echo "All services started!"
echo "Close the windows or press Ctrl+C in each to stop them."

