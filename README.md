# 🤖 J.A.R.V.I.S. — Stark Industries Tactical Directive Board

[![GitHub Repo](https://img.shields.io/badge/GitHub-Mahmadyaseen06%2FJarvis-00f0ff?logo=github)](https://github.com/Mahmadyaseen06/Jarvis)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemma 4](https://img.shields.io/badge/Model-Gemma--4--Instruct-f59e0b?logo=google)](https://huggingface.co/google/gemma-4-instruct)

An authentic **Iron Man J.A.R.V.I.S.**-themed Voice-First Tactical Task Board web application built with **FastAPI**, **vanilla HTML/JS**, and **Google Gemma 4** (`google/gemma-4-instruct`).

Control your engineering directives purely with your voice: command J.A.R.V.I.S. to catalog tasks with priority ratings, transition cards across tactical columns, and receive British-mannered audio confirmations from Tony Stark's personal AI assistant.

---

## ✨ Features

- **Iron Man J.A.R.V.I.S. Voice Persona & Core**:
  - **Pulsing Arc Reactor Core**: Central interactive Arc Reactor button with holographic HUD degree markings and real-time audio waveform visualizer.
  - **Speech Recognition**: Browser-native **Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)**.
  - **Authentic British Spoken Output**: Speaks aloud in J.A.R.V.I.S. character (*"Right away, Sir. Added to the directive queue."*, *"Directive completed, Sir. Outstanding work."*).
- **Procedural Stark HUD Sound FX (Web Audio API)**:
  - Zero external MP3/audio file dependencies. Generates authentic sci-fi frequency beeps for voice activation, directive moves, additions, and deletions (with mute switch).
- **Stark Industries Tactical Columns (`index.html`)**:
  - Columns: **🛡️ Backlog Directives** (To Do), **⚡ In Operation** (In Progress), **🎯 Mission Accomplished** (Done).
  - **Native HTML5 Drag & Drop**: Silky physical card dragging between all 3 columns with holographic cyan border glow.
  - **Live Progress & Metrics**: Real-time completion tracker (`PROGRESS: X% (Done/Total)`).
  - **Search & Priority Filtering**: Instant directive search and priority filter toggles (**All**, **High Priority**, **Low Priority**).
  - **LocalStorage Persistence**: Directives stay saved across browser refreshes, with a pre-loaded Stark directive suite.
- **FastAPI + Gemma 4 PM Engine (`main.py`)**:
  - Full CORS-enabled FastAPI backend.
  - Conversational context memory preserved across turns in global `chat_history`.
  - Structured JSON action dispatch (`ADD_TASK`, `MOVE_TASK`, `CLEAR_ALL`, `NONE`).
  - Supports conversational shortcuts (*"Mark flight thrusters as done"*, *"Start working on repulsors"*, *"Purge display"*).
  - Zero-latency offline fallback engine ensures 100% functionality even when offline.

---

## 🏗️ Architecture & Action Schema

The Gemma 4 system prompt enforces structured JSON responses:

```json
{
  "reply": "Right away, Sir. Added 'Calibrate Mark 85 Flight Systems' to the backlog with High priority.",
  "action": {
    "command": "ADD_TASK",
    "task_name": "Calibrate Mark 85 Flight Systems",
    "priority": "High"
  }
}
```

Supported Commands:
- `ADD_TASK`: Requires `task_name` (string) and `priority` (`High` or `Low`).
- `MOVE_TASK`: Requires `task_name` (string) and `new_status` (`Todo`, `InProgress`, or `Done`).
- `CLEAR_ALL`: Clears all directives on the tactical board.
- `NONE`: Conversational queries or status updates.

---

## 🚀 Quick Setup & Run Instructions

### 1. Prerequisites
- Python 3.9+ (Python 3.10 – 3.14 recommended)
- Browser: **Google Chrome** (recommended for native Web Speech API support)

### 2. Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/Mahmadyaseen06/Jarvis.git
cd Jarvis

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Configure Gemma 4 API Key

```bash
cp .env.example .env
```

Add your Hugging Face user access token in `.env`:
```env
GEMMA_API_KEY=hf_your_huggingface_token_here
```

*(Note: If omitted, the application runs on its built-in J.A.R.V.I.S. fallback engine with zero delay!)*

### 4. Run the Application

```bash
# Option A: Run convenience script
./run.sh

# Option B: Run python launcher
python3 run.py

# Option C: Direct uvicorn command
uvicorn main:app --reload --port 8000
```

### 5. Access the Web App

Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🎯 60-Second Live J.A.R.V.I.S. Demo Script

1. **Activate Voice HUD**:
   - Click the glowing **Arc Reactor** in the center. The core turns tactical red and J.A.R.V.I.S. begins listening.
2. **Issue a High-Priority Directive**:
   - Speak:
     > *"J.A.R.V.I.S., add a task to calibrate Mark 85 flight thrusters with high priority"*
   - 🔊 J.A.R.V.I.S. responds aloud: *"Right away, Sir. Added 'Calibrate Mark 85 Flight Thrusters' to the backlog with High priority."*
   - A crimson `HIGH` priority card appears in **Backlog Directives**.
3. **Transition to Active Operation**:
   - Speak:
     > *"Move Mark 85 flight thrusters to In Progress"*
   - ⚡ Card glides into **In Operation** and a sleek Stark HUD whoosh chime plays.
4. **Complete the Directive**:
   - Speak:
     > *"Mark Mark 85 flight thrusters as done"*
   - 🎯 J.A.R.V.I.S. responds: *"Protocol 'Calibrate Mark 85 Flight Thrusters' marked as accomplished, Sir. Outstanding work."* Card moves to **Mission Accomplished**.
5. **Purge Protocols**:
   - Speak:
     > *"J.A.R.V.I.S., clear the board"*
   - 🗑️ J.A.R.V.I.S. responds: *"Clearing all directives from the Stark tactical display, Sir."*

---

## 🧪 Automated Integration Tests

Run the full end-to-end backend test suite:

```bash
python3 test_app.py
```

Validates:
- Frontend HTML delivery at `GET /`
- Structured JSON output for `ADD_TASK` (High and Low priority)
- State transitions for `MOVE_TASK` to `InProgress` and `Done`
- Task board reset via `CLEAR_ALL`
- Conversational context preservation in `GET /history`
- Session reset via `POST /clear`

---

## 📁 Project Structure

```
Jarvis/
├── main.py              # FastAPI server, Gemma 4 LLM client & J.A.R.V.I.S. router
├── index.html           # Iron Man Arc Reactor HUD UI with Web Speech API
├── requirements.txt     # Python dependencies (fastapi, uvicorn, pydantic, huggingface_hub)
├── test_app.py          # Integration test suite validating API & actions
├── run.sh               # Quick startup shell script with virtualenv auto-detection
├── run.py               # Cross-platform Python server launcher
├── .env.example         # Template for GEMMA_API_KEY / HF_TOKEN
├── NOTES.md             # Development post-mortem & bug notes log
└── README.md            # Project documentation and demo script
```
