#!/bin/sh
set -e

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}
PARSER_PORT=${PARSER_PORT:-5600}

echo "Starting MatchMentor Backend..."
echo "Using Port: $PORT"

# Function to start the parser in a loop
start_parser() {
    while true; do
        if [ -f "parser.jar" ]; then
            echo "Starting OpenDota parser on port $PARSER_PORT..."
            # Increase heap to 2GB to handle large 160MB replays safely
            java -Xmx2048M -Xms512M -jar parser.jar $PARSER_PORT
            echo "Parser process exited with code $?. Restarting in 2 seconds..."
            sleep 2
        else
            echo "ERROR: parser.jar not found. Replay parsing will be unavailable."
            sleep 10
        fi
    done
}

# Start parser service in background loop
start_parser &
PARSER_PID=$!
echo "Parser loop started in background (PID: $PARSER_PID)"

# Wait for parser to be ready
echo "Waiting for parser to initialize..."
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:$PARSER_PORT/healthz" > /dev/null; then
        echo "✓ Parser is ready"
        break
    fi
    echo "Waiting for parser... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "WARNING: Parser failed to start after $MAX_RETRIES retries."
fi

# Start Uvicorn using exec to replace the shell process
echo "Starting FastAPI on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT

