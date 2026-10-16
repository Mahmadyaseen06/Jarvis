# 📋 Voice-Controlled AI Task Board

A voice-first, AI-powered Kanban project management web application built with **FastAPI**, **vanilla HTML/JS**, and **Google Gemma 4** (`google/gemma-4-instruct`).

Control your project workflow purely with your voice: add tasks with priority ratings, transition cards across Kanban columns, and manage project progress with spoken voice confirmations.

---

## ✨ Features

- **Voice-In, Voice-Out Loop**:
  - **Speech Recognition**: Captures microphone audio using the browser's native **Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)**.
  - **Tactile "Hold to Speak" Button**: Hold or tap to record voice instructions with dynamic visualizer rings and real-time interim transcription feedback.
  - **Spoken AI Responses**: Speaks assistant confirmations aloud using **`speechSynthesis`**.
- **Google Gemma 4 AI Project Manager Backend (`main.py`)**:
  - FastAPI backend with full CORS support.
  - Conversational context memory preserved across turns in global `chat_history`.
  - Powered by `huggingface_hub.InferenceClient` calling `google/gemma-4-instruct` (configured with `GEMMA_API_KEY`).
  - Strict system prompt enforces structured raw JSON schema with spoken `reply` and `action` commands.
  - Built-in zero-latency fallback engine ensures 100% offline functionality if no API key is set.
- **Dynamic 3-Column Kanban Board (`index.html`)**:
  - Columns: **To Do**, **In Progress**, **Done** with live item count badges and empty-state placeholders.
  - **`ADD_TASK`**: Spawns task cards with priority badges (**High** in crimson, **Low** in cyan) and timestamps.
  - **`MOVE_TASK`**: Synchronous atomic DOM moves with exact & fuzzy title matching.
  - **`CLEAR_ALL`**: Safely clears all task cards from the board.
  - Manual controls: Individual card deletion buttons, quick text command input, and example command chips.

---

## 🏗️ Architecture & Action Schema

### Backend Action Dispatch

The Gemma 4 system prompt enforces structured JSON responses:

```json
{
  "reply": "Added 'Design Landing Page' to To Do with High priority.",
  "action": {
    "command": "ADD_TASK",
    "task_name": "Design Landing Page",
    "priority": "High"
  }
}
```

Supported Commands:
- `ADD_TASK`: Requires `task_name` (string) and `priority` (`High` or `Low`).
- `MOVE_TASK`: Requires `task_name` (string) and `new_status` (`Todo`, `InProgress`, or `Done`).
- `CLEAR_ALL`: Clears all tasks on the board.
- `NONE`: Conversational query or unrecognized intent.

---

## 🚀 Quick Setup & Run Instructions

### 1. Prerequisites
- Python 3.9+ (Python 3.10 – 3.14 recommended)
- Modern browser: **Google Chrome** (recommended for full continuous Web Speech support), Microsoft Edge, or Safari.

### 2. Environment Setup

```bash
# 1. Clone or navigate to the project directory
cd Jarvis

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Configure Gemma 4 API Key

To enable Google Gemma 4 via Hugging Face Inference:

```bash
cp .env.example .env
```

Add your Hugging Face user access token in `.env`:
```env
GEMMA_API_KEY=hf_your_huggingface_token_here
```

*(Note: If omitted, the application seamlessly runs on its built-in rule-based PM fallback engine with zero delay!)*

### 4. Run the Application

You can start the server with any of the following:

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
*(FastAPI directly serves `index.html` at `/`, ensuring proper `http://` origin security for microphone access).*

---

## 🎯 60-Second Live Demo Script

1. **Open the Task Board**:
   - Navigate to `http://localhost:8000`. Notice the dark futuristic UI and the 3 columns ("To Do", "In Progress", "Done").
2. **Add a High Priority Task**:
   - Press and hold **"HOLD TO SPEAK"** (or click once to toggle) and say:
     > *"Add a task to build authentication API with high priority"*
   - The AI responds aloud: *"Added 'Build Authentication Api' to To Do with High priority."*
   - A new card appears in the **To Do** column with a red `HIGH` badge.
3. **Add a Low Priority Task**:
   - Speak:
     > *"Create a task to update documentation with low priority"*
   - A second card is created with a cyan `LOW` badge.
4. **Move the Task Across the Board**:
   - Speak:
     > *"Move Authentication API to In Progress"*
   - The card instantly transitions to the **In Progress** column, and the column counters update in real time.
5. **Complete the Task**:
   - Speak:
     > *"Move Authentication API to Done"*
   - The card moves to **Done**.
6. **Clear the Board**:
   - Speak:
     > *"Clear the task board"*
   - All cards are safely removed, returning columns to their empty state.

---

## 🧪 Automated Integration Tests

Run the full end-to-end backend test suite:

```bash
python3 test_app.py
```

---

## 📁 Project Structure

```
Jarvis/
├── main.py              # FastAPI server, Gemma 4 LLM client & action router
├── index.html           # Dark-mode futuristic Kanban UI with Web Speech API
├── requirements.txt     # Python dependencies (fastapi, uvicorn, pydantic, huggingface_hub)
├── test_app.py          # Integration test suite validating API & actions
├── run.sh               # Quick startup shell script with virtualenv auto-detection
├── run.py               # Cross-platform Python server launcher
├── .env.example         # Template for GEMMA_API_KEY / HF_TOKEN
├── NOTES.md             # Development post-mortem & bug notes log
└── README.md            # Project documentation and demo script
```
