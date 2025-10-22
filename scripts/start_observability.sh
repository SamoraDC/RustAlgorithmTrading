#!/bin/bash
# Start the Observability API server

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r src/observability/requirements.txt
fi

# Parse command line arguments
DEV_MODE=""
WORKERS="4"
HOST="127.0.0.1"
PORT="8000"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE="--dev"
            shift
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Start the server
echo "Starting Observability API..."
echo "  Host: $HOST"
echo "  Port: $PORT"

if [ -n "$DEV_MODE" ]; then
    echo "  Mode: Development (auto-reload enabled)"
    python src/observability/server.py \
        --dev \
        --host "$HOST" \
        --port "$PORT" \
        --log-level DEBUG
else
    echo "  Mode: Production"
    echo "  Workers: $WORKERS"
    python src/observability/server.py \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level INFO
fi
