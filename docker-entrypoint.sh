#!/bin/bash
set -e

# Add the current directory to PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Debug prints
echo "Current directory: $(pwd)"
echo "PYTHONPATH: $PYTHONPATH"
echo "Directory contents: $(ls -la)"
echo "Python sys.path: $(python -c 'import sys; print(sys.path)')"

# Create data directory if it doesn't exist
mkdir -p /app/data

# Setup the database
echo "Setting up database..."
python src/main.py --mode setup_db

# Start the server
echo "Starting server..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000 