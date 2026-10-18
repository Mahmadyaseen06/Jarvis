# J.A.R.V.I.S. — Voice-Controlled HUD Dashboard

[![GitHub Repo](https://img.shields.io/badge/GitHub-Mahmadyaseen06%2FJarvis-181717?logo=github)](https://github.com/Mahmadyaseen06/Jarvis)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight, real-time web dashboard for voice-activated UI interactions. Built with **FastAPI**, **vanilla JavaScript**, and **Hugging Face Inference Endpoint LLMs** (with built-in rule-based offline fallback).

---

## 📸 Overview & Architecture

The application operates as a single-page interactive HUD that processes voice commands using browser-native APIs and triggers dynamic front-end state changes based on structured responses from the backend.

┌─────────────────────────┐          HTTP / POST          ┌──────────────────────────┐
│                         │  ───────────────────────────> │                          │
│   Web Browser (Client)  │           /api/chat           │     FastAPI Backend      │
│   - Web Speech API      │                               │   - Gemma Instruct LLM   │
│   - Web Audio Canvas    │ <───────────────────────────  │   - Fallback Rule Engine │
│                         │          JSON Action          │                          │
└─────────────────────────┘                               └──────────────────────────┘

### Key Technical Capabilities
* **Voice Synthesis & Recognition:** Utilizes Web Speech API (`webkitSpeechRecognition` & `speechSynthesis`) for real-time speech-to-text and text-to-speech.
* **Audio Visualization:** Real-time microphone audio input waveform rendered via standard HTML5 Canvas and Web Audio API `AnalyserNode`.
* **Dynamic Action Handler:** The client intercepts structured JSON responses from the backend to execute UI state modifications (`SYSTEM_SCAN`, `ACTIVATE_DEFENSE`, `DEPLOY_WIDGET`, `STAND_DOWN`).
* **Zero-Latency Fallback Engine:** Functions entirely offline using a regex-based parser when Hugging Face API keys are absent or unreachable.

---

## 🛠 Action Protocol Schema

All API responses from `/api/chat` adhere to the following JSON schema:

```json
{
  "reply": "Initiating system scan across all active holographic arrays.",
  "action": {
    "command": "SYSTEM_SCAN",
    "widget_name": null
  }
}

Supported Commands
Command	Action Effect	Sample Query
SYSTEM_SCAN	Triggers UI laser sweep animation and streams diagnostic logs.	"Run a full diagnostic scan"
ACTIVATE_DEFENSE	Alters UI theme to high-contrast red alert state and displays alert banner.	"Engage defense protocols"
DEPLOY_WIDGET	Spawns a floating telemetry card matching widget_name.	"Deploy Arc Reactor widget"
STAND_DOWN	Reverts UI state to default cyan theme and closes alert banners.	"Stand down, return to normal"
NONE	Standard conversational LLM text response with no UI side effects.	"What is your current status?"
🚀 Installation & Local Development
Prerequisites
Python: 3.10 or higher

Browser: Chrome, Edge, or Brave (required for Web Speech API speech-to-text support)

Setup
Clone the repository:

Bash
git clone [https://github.com/Mahmadyaseen06/Jarvis.git](https://github.com/Mahmadyaseen06/Jarvis.git)
cd Jarvis
Set up virtual environment:

Bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
Install dependencies:

Bash
pip install -r requirements.txt
Environment Configuration (Optional):
Copy the .env.example file to create a .env file:

Bash
cp .env.example .env
Add your Hugging Face API token if you wish to use an external LLM endpoint:

Code snippet
GEMMA_API_KEY=hf_your_token_here
Note: If no token is provided, the backend seamlessly degrades to the local rule engine.

🏃 Running the Server
Start the development server using any of the following options:

Bash
# Option 1: Direct Uvicorn invocation
uvicorn main:app --reload --port 8000

# Option 2: Python launcher
python3 run.py

# Option 3: Shell script
./run.sh
Access the UI at http://localhost:8000.

🧪 Testing
Run the automated backend test suite to verify route response formats and action parsing logic:

Bash
python3 test_app.py
📁 Repository Layout
.
├── main.py              # FastAPI application & LLM/fallback routing logic
├── index.html           # Front-end HUD interface, JS speech engine, & CSS themes
├── requirements.txt     # Python runtime dependencies
├── test_app.py          # End-to-end endpoint tests
├── run.py               # Cross-platform application entry point
├── run.sh               # Shell script launcher
└── .env.example         # Environment template

<FollowUp>
Would you like me to adjust any specific command definitions or environment configurations in this setup?
</FollowUp>
