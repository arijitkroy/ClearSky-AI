#!/bin/sh

# Start simulator in background if not explicitly disabled (e.g., in local docker-compose)
if [ "$START_SIMULATOR" != "false" ]; then
    echo "Starting IoT Air Quality Simulator in background..."
    python simulator/simulator.py &
else
    echo "IoT Air Quality Simulator is disabled in this container."
fi

# Start backend in foreground on the port specified by Render (defaults to 8000)
# Render passes the PORT env variable automatically.
PORT=${PORT:-7860}
echo "Starting FastAPI backend on port $PORT..."
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
