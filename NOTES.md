# Project Notes & Post-Mortem Log

This file tracks approaches tried, lessons learned, and failure modes to avoid repeating mistakes during development.

## Log
- Initialized repository with FastAPI backend and Voice-First Web Speech frontend.
- Note: String splitting on transcribed user text can include trailing punctuation (e.g. "Alex."); added `.strip(".!?, ")` to ensure clean entity memory extraction.
- Note: Using httpx with starlette TestClient emits a deprecation warning on latest Starlette versions, but does not affect production Uvicorn runtime.
- Note: Running `uvicorn` in a bare shell fails with `command not found: uvicorn` if `.venv` is not activated. Added `run.sh`, `run.py`, and direct `.venv/bin/uvicorn` instructions to provide single-command execution.
- Fixed CSS lint warning: added standard `background-clip: text` alongside `-webkit-background-clip: text`.
- Note: Opening `index.html` via `file://` causes browser security blocks: Chrome/Safari disable Web Speech API recognition on `file://` origins and `window.location.origin` becomes "null". Added dynamic fallback to `http://127.0.0.1:8000`, explicit in-app warning banner with clickable URL, and `SpeechSynthesis.resume()` for Chrome audio engine.
- Note: Web Speech API with `continuous = false` shuts off after 4-5s of silence with benign `no-speech` error. Fixed by setting `continuous = true`, auto-reconnecting on `onend`, adding configurable language/accent (`en-IN`, `en-US`), pause detection timer (1.4s), and manual 'Send Speech Now' button.
- Note: In Safari on macOS (WebKit), setting `recognition.continuous = true` causes WebKit to immediately abort speech recognition with a fatal `network` error. Fixed by detecting Safari (`continuous = false` on Safari, `true` on Chrome), auto-fallback from `en-IN` to global `en-US` if speech server is unreachable, and adding clear macOS Dictation / Chrome browser guidance.
- Verified: End-to-end voice loop operational in Google Chrome. Real-time microphone capture, conversation memory tracking in FastAPI, and spoken audio response verified.
- Implemented: Gemma 4 Voice Diner app with `huggingface_hub.InferenceClient` calling `google/gemma-4-instruct`, structured JSON action dispatch (ADD_PIZZA, ADD_BURGER, CLEAR_CART, NONE), Hold-to-Speak native Web Speech button, and visual animated cart UI.
- Expanded: Added `ADD_FRIES` (🍟 $4.50) and `ADD_DRINK` (🥤 $2.95) actions and speech quantity extraction (e.g. "three pizzas", "2 burgers"). Cart groups items with quantity multipliers and calculates exact totals.
- Redesigned UI: Transformed frontend into an authentic, dedicated **Gemma Voice Diner** drive-thru intercom. Features a physical tactile "HOLD TO TALK" button with ON-AIR LED, interactive food menu strip, dynamic takeout tray, tax/total calculation, and a live thermal kitchen ticket feed. All traces of generic sci-fi Jarvis styling removed.
- Implemented: Voice-Controlled AI Task Board with dark-mode futuristic Kanban board ("To Do", "In Progress", "Done"), Hold-to-Speak native Web Speech button, SpeechSynthesis, and Gemma 4 AI Project Manager action dispatch (`ADD_TASK`, `MOVE_TASK`, `CLEAR_ALL`, `NONE`). Verified DOM card manipulation and fuzzy title matching.
- Reverted to 074c9bd and applied minimal patch: Eliminated DOM parent-child hierarchy race condition by replacing asynchronous setTimeout with synchronous atomic moves (`destContainer.appendChild`), added safe `card.parentElement.removeChild` checks, updated counters dynamically, and preserved interim+final speech in `spokenText` so button release never drops transcribed voice.






