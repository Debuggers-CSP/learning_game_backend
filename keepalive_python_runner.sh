#!/bin/bash

# Keepalive script for Python runner
# This ensures the Python code execution backend stays online

RUNNER_PORT=${PYTHON_RUNNER_PORT:-5001}
LOG_FILE="python_runner.log"
BACKEND_DIR="/home/rishabh2010/learning_game_backend"

cd "$BACKEND_DIR" || exit 1

while true; do
    # Check if Python runner is responding
    if ! curl -sf http://127.0.0.1:${RUNNER_PORT}/health > /dev/null 2>&1; then
        echo "[$(date)] Python runner is down. Restarting..." | tee -a keepalive.log
        
        # Kill any existing process
        pkill -f "python.*python_backend/app.py" 2>/dev/null || true
        sleep 1
        
        # Start the runner
        PYTHON_RUNNER_PORT=${RUNNER_PORT} python3 python_backend/app.py > "$LOG_FILE" 2>&1 &
        RUNNER_PID=$!
        
        sleep 2
        
        # Verify it started
        if curl -sf http://127.0.0.1:${RUNNER_PORT}/health > /dev/null 2>&1; then
            echo "[$(date)] Python runner restarted successfully (PID: $RUNNER_PID)" | tee -a keepalive.log
        else
            echo "[$(date)] Failed to restart Python runner. Check $LOG_FILE" | tee -a keepalive.log
        fi
    fi
    
    # Check every 10 seconds
    sleep 10
done
