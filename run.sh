#!/bin/bash
# Automatically activate venv and run uvicorn
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Free port 8000 if occupied by another process to prevent [Errno 48] Address already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚡ Port 8000 is occupied by an existing process. Reclaiming port..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 0.5
fi

echo "🎙️ Starting J.A.R.V.I.S. Neural Console on http://127.0.0.1:8000..."

if [ -f ".venv/bin/uvicorn" ]; then
    exec .venv/bin/uvicorn main:app --reload --port 8000
else
    echo "Virtual environment not found. Activating system python..."
    python3 -m uvicorn main:app --reload --port 8000
fi

