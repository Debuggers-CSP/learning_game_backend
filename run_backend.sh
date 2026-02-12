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

# Run the Flask app
export FLASK_PORT=${FLASK_PORT:-4000}
echo "✓ Starting Flask on http://localhost:${FLASK_PORT}"
echo ""
PYTHON_RUNNER_PORT=${PYTHON_RUNNER_PORT:-5001}
if [ -f "python_backend/app.py" ]; then
    echo "✓ Starting Python runner on http://localhost:${PYTHON_RUNNER_PORT}"
    PYTHON_RUNNER_PORT=${PYTHON_RUNNER_PORT} python python_backend/app.py > python_runner.log 2>&1 &
fi

python main.py

