# 🤖 J.A.R.V.I.S. — Holographic AI System Dashboard

[![GitHub Repo](https://img.shields.io/badge/GitHub-Mahmadyaseen06%2FJarvis-00f0ff?logo=github)](https://github.com/Mahmadyaseen06/Jarvis)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemma 4](https://img.shields.io/badge/Model-Gemma--4--Instruct-f59e0b?logo=google)](https://huggingface.co/google/gemma-4-instruct)

An authentic **Iron Man J.A.R.V.I.S.** Holographic AI System Dashboard built with **FastAPI**, **vanilla HTML/JS**, and **Google Gemma 4** (`google/gemma-4-instruct`).

Control your holographic command center purely through voice: command J.A.R.V.I.S. to sweep diagnostic lasers across the screen, engage red alert defense protocols, deploy live data widgets to the HUD, and chat with Tony Stark's personal AI assistant.

---

## ✨ Features

- **J.A.R.V.I.S. Sci-Fi HUD Command Center (`index.html`)**:
  - Dark-mode high-tech aesthetic (`#0a0a0a`) with glowing cyan/blue accents and monospace grid lines.
  - Animated **"Voice Link Active"** button with a pulsating holographic glow ring while listening.
  - Real-time audio waveform canvas visualizer driven by the Web Audio API.
  - Robotic/British spoken audio confirmations via tuned `speechSynthesis.getVoices()`.
- **Holographic System Commands**:
  - 🔬 **`SYSTEM_SCAN`**: Triggers a laser line sweep animation across the screen and prints live matrix-style diagnostic telemetry.
  - 🚨 **`ACTIVATE_DEFENSE`**: Instantly transforms glowing accents from cyan to emergency red and flashes a high-voltage `"DEFENSE PROTOCOLS ENGAGED"` alert banner.
  - 📊 **`DEPLOY_WIDGET`**: Dynamically creates glowing glassmorphism cards on the dashboard displaying the `widget_name` provided by Gemma (e.g. Arc Reactor Output, Repulsor Grid, Orbital Satlink).
  - 💬 **`NONE`**: Concise, witty, British-mannered conversational AI banter.
- **FastAPI + Gemma 4 Backend (`main.py`)**:
  - Full CORS-enabled FastAPI backend serving both API and frontend.
  - Multi-turn conversation history tracked in global `chat_history`.
  - Powered by `huggingface_hub.InferenceClient` calling `google/gemma-4-instruct`.
  - Built-in offline fallback engine guarantees 100% functionality without requiring external API keys.

---

## 🏗️ Architecture & Action Schema

The Gemma 4 system prompt enforces structured JSON responses:

```json
{
  "reply": "Initiating comprehensive diagnostic scan across all holographic arrays. Stand by, Sir.",
  "action": {
    "command": "SYSTEM_SCAN"
  }
}
```

### Available Commands

| Command | Action Effect | Example Voice Prompt |
|---|---|---|
| `SYSTEM_SCAN` | Sweeps laser across screen & streams diagnostic matrix | *"Jarvis, run a full system scan"* |
| `ACTIVATE_DEFENSE` | Turns HUD to emergency red & flashes alert banner | *"Engage defense protocols / red alert"* |
| `DEPLOY_WIDGET` | Deploys glassmorphism widget with `widget_name` | *"Deploy widget Arc Reactor Output"* |
| `NONE` | Natural conversational dialog with J.A.R.V.I.S. | *"Hello Jarvis, what is your status?"* |

---

## 🚀 Quick Setup & Run Instructions

### 1. Prerequisites
- Python 3.9+ (Python 3.10 – 3.14 recommended)
- Browser: **Google Chrome** (recommended for Web Speech API support)

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

*(Note: If omitted, the application runs on its built-in rule-based J.A.R.V.I.S. engine with zero delay!)*

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

1. **Activate Voice Link**:
   - Click the glowing **Voice Link** button. The ring pulses red and J.A.R.V.I.S. begins listening.
2. **Execute System Diagnostic**:
   - Speak:
     > *"Jarvis, run a full system scan"*
   - 🔊 A glowing laser line sweeps across the screen while diagnostic telemetry floods the console.
3. **Engage Defense Protocols**:
   - Speak:
     > *"Engage defense protocols and activate red alert"*
   - 🚨 The entire HUD switches from cyan to tactical emergency red, flashing the alert banner.
4. **Deploy Live Data Widgets**:
   - Speak:
     > *"Deploy widget Arc Reactor Thermal Output"*
   - 📊 A glowing glassmorphism telemetry widget appears on the HUD with live efficiency meters.
5. **Stand Down**:
   - Speak:
     > *"Stand down Jarvis, return to normal mode"*
   - 🟢 Systems return to calm cyan standby status.

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
├── main.py              # FastAPI server, Gemma 4 LLM client & J.A.R.V.I.S. router
├── index.html           # Holographic Sci-Fi HUD UI with Web Speech API
├── requirements.txt     # Python dependencies (fastapi, uvicorn, pydantic, huggingface_hub)
├── test_app.py          # Integration test suite validating all commands
├── run.sh               # Quick startup shell script with virtualenv auto-detection
├── run.py               # Cross-platform Python server launcher
├── .env.example         # Template for GEMMA_API_KEY / HF_TOKEN
├── NOTES.md             # Development post-mortem & bug notes log
└── README.md            # Project documentation and demo script
```
