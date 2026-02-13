#!/bin/bash

# Quick script to run the Flask backend

echo "🚀 Starting Flask Backend..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found! Run setup_and_run.sh first"
    exit 1
fi

# Kill any existing python_backend processes and keepalive script
pkill -f "python.*python_backend/app.py" 2>/dev/null || true
pkill -f "keepalive_python_runner.sh" 2>/dev/null || true

# Run the Flask app
export FLASK_PORT=${FLASK_PORT:-3000}
echo "✓ Starting Flask on http://localhost:${FLASK_PORT}"
echo ""
PYTHON_RUNNER_PORT=${PYTHON_RUNNER_PORT:-5001}
if [ -f "python_backend/app.py" ]; then
    echo "✓ Starting Python runner on http://localhost:${PYTHON_RUNNER_PORT}"
    PYTHON_RUNNER_PORT=${PYTHON_RUNNER_PORT} python3 python_backend/app.py > python_runner.log 2>&1 &
    PYTHON_RUNNER_PID=$!
    sleep 1
    if ps -p $PYTHON_RUNNER_PID > /dev/null; then
        echo "✓ Python runner started successfully (PID: $PYTHON_RUNNER_PID)"
        
        # Start keepalive script in background
        if [ -f "keepalive_python_runner.sh" ]; then
            ./keepalive_python_runner.sh > /dev/null 2>&1 &
            echo "✓ Keepalive monitor started (auto-restart enabled)"
        fi
    else
        echo "⚠️  Python runner failed to start, check python_runner.log"
    fi
fi

python main.py

