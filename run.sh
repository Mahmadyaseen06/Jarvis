#!/bin/bash
# Automatically activate venv and run uvicorn
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/uvicorn" ]; then
    echo "🎙️ Starting Jarvis Voice-First Assistant via .venv..."
    exec .venv/bin/uvicorn main:app --reload --port 8000
else
    echo "Virtual environment not found. Activating system python..."
    python3 -m uvicorn main:app --reload --port 8000
fi
