# Project Notes & Post-Mortem Log

This file tracks approaches tried, lessons learned, and failure modes to avoid repeating mistakes during development.

## Log
- Initialized repository with FastAPI backend and Voice-First Web Speech frontend.
- Note: String splitting on transcribed user text can include trailing punctuation (e.g. "Alex."); added `.strip(".!?, ")` to ensure clean entity memory extraction.
- Note: Using httpx with starlette TestClient emits a deprecation warning on latest Starlette versions, but does not affect production Uvicorn runtime.
- Note: Background network daemon socket binding (`bind()`) is restricted inside the sandboxed environment (`[Errno 1] Operation not permitted`); verified full FastAPI ASGI stack, HTML rendering, and multi-turn voice chat history via in-process ASGI TestClient test suite.


