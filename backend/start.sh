#!/bin/sh
set -e

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}
PARSER_PORT=${PARSER_PORT:-5600}

echo "Starting MatchMentor Backend..."
echo "Using Port: $PORT"

# Verify parser jar exists
if [ -f "parser.jar" ]; then
    echo "Parser JAR found: $(ls -lh parser.jar)"
    
    # Start parser service in background
    echo "Starting OpenDota parser on port $PARSER_PORT..."
    java -jar parser.jar $PARSER_PORT > /tmp/parser.log 2>&1 &
    PARSER_PID=$!
    echo "Parser started with PID: $PARSER_PID"
    
    # Wait for parser to be ready
    echo "Waiting for parser to initialize..."
    sleep 5
    
    # Test if parser is responding
    if curl -s http://localhost:$PARSER_PORT > /dev/null; then
        echo "✓ Parser is ready"
    else
        echo "WARNING: Parser may not be ready, but continuing..."
    fi
else
    echo "WARNING: Parser JAR not found! .dem parsing will be unavailable."
fi

# Start Uvicorn using exec to replace the shell process
echo "Starting FastAPI on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT

