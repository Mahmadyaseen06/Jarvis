# Project Notes & Post-Mortem Log

This file tracks approaches tried, lessons learned, and failure modes to avoid repeating mistakes during development.

## Log
- Initialized repository with FastAPI backend and Voice-First Web Speech frontend.
- Note: String splitting on transcribed user text can include trailing punctuation (e.g. "Alex."); added `.strip(".!?, ")` to ensure clean entity memory extraction.
- Note: Using httpx with starlette TestClient emits a deprecation warning on latest Starlette versions, but does not affect production Uvicorn runtime.
- Note: Running `uvicorn` in a bare shell fails with `command not found: uvicorn` if `.venv` is not activated. Added `run.sh`, `run.py`, and direct `.venv/bin/uvicorn` instructions to provide single-command execution.
- Fixed CSS lint warning: added standard `background-clip: text` alongside `-webkit-background-clip: text`.


