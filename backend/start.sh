#!/bin/sh
set -e

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}

echo "Starting MatchMentor Backend..."
echo "Using Port: $PORT"

# Verify clarity jar exists
if [ -f "clarity.jar" ]; then
    echo "Clarity JAR found: $(ls -lh clarity.jar)"
else
    echo "WARNING: Clarity JAR not found!"
fi

# Start Uvicorn using exec to replace the shell process
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
