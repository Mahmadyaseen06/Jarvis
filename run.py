#!/usr/bin/env python3
"""
Convenience launcher for Jarvis Voice Assistant.
Automatically uses the virtual environment uvicorn binary.
"""
import os
import sys
import subprocess

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    venv_uvicorn = os.path.join(root, ".venv", "bin", "uvicorn")
    
    if os.path.exists(venv_uvicorn):
        cmd = [venv_uvicorn, "main:app", "--reload", "--port", "8000"]
    else:
        cmd = [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"]
    
    print(f"🎙️ Launching Jarvis Voice-First Assistant on http://localhost:8000 ...")
    try:
        sys.exit(subprocess.call(cmd))
    except KeyboardInterrupt:
        print("\nShutting down Jarvis server.")

if __name__ == "__main__":
    main()
