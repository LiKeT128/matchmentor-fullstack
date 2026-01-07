#!/bin/bash
set -e

echo "DYNO Startup Script"
echo "Current directory: $(pwd)"

echo "Running Alembic database migrations..."
# Use python -m alembic to avoid path issues
python -m alembic upgrade head

echo "Migration complete. Current revision:"
python -m alembic current

echo "Starting MatchMentor backend..."
exec "$@"
