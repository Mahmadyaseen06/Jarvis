# 🎙️ Jarvis: Voice-First AI Assistant (Hackathon Edition)

A high-performance, Voice-First AI assistant application built for hackathons and live stage demonstrations. Features a real-time conversational **FastAPI** backend with multi-turn conversation memory and a futuristic **Web Speech API + SpeechSynthesis** frontend.

---

## ✨ Features

- **Real-Time Voice-In, Voice-Out Loop**:
  - Captures microphone audio using the browser's native **Web Speech API (`SpeechRecognition`)**.
  - Speaks responses aloud using **SpeechSynthesis API (`speechSynthesis`)**.
  - Includes voice selector (Samantha, Google US English, Daniel, etc.), rate, and pitch controls.
- **FastAPI Backend (`main.py`)**:
  - `/chat` endpoint receiving speech transcriptions and tracking conversation history per session.
  - Pluggable AI: Works immediately out-of-the-box with a built-in contextual fallback conversational engine, or seamlessly connects to **OpenAI** (`gpt-4o-mini`) or **Gemini** (`gemini-1.5-flash`) via `.env`.
  - Multi-turn conversational memory (e.g., remember user names, context, and past questions).
  - `/history/{session_id}` and `/reset` endpoints for transparent session management.
- **Hackathon-Ready Voice Stage UI (`index.html`)**:
  - Cybernetic glowing Voice Orb with real-time waveform visualizer canvas.
  - Real-time interim transcription display (shows what you're saying as you speak).
  - Continuous Conversation Mode toggle (hands-free back-and-forth chat loop).
  - Stop/Cut-off speech button for instant interruptions.
  - Fallback text input bar for noisy hackathon presentation halls.

---

## 🚀 Quick Setup & Run Instructions

### 1. Prerequisites
- Python 3.9+ (tested on Python 3.10 - 3.14)
- Google Chrome, Microsoft Edge, or Safari (for native Web Speech API support)

### 2. Environment Setup

```bash
# 1. Clone or navigate into the Jarvis project directory
cd Jarvis

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Configure External LLM Keys
Jarvis runs completely offline with its intelligent conversational fallback memory engine. To plug into OpenAI or Gemini for unrestricted open-ended intelligence:

```bash
cp .env.example .env
```
Edit `.env` and add:
```env
OPENAI_API_KEY=your_openai_api_key_here
# or
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run the Application

Start the FastAPI backend with hot-reload enabled:

```bash
uvicorn main:app --reload --port 8000
```

### 5. Open in Your Browser
Open your browser and navigate to:
```
http://localhost:8000
```
*(FastAPI directly serves the frontend at `/` so no separate HTTP server is required!)*

---

## 🎯 Live Hackathon Demo Script (60 Seconds)

1. **Click the Glowing Orb** (or "Start Listening") and grant microphone permissions if prompted.
2. **Speak Naturally**:
   > *"Hello! My name is Alex. What can you do?"*
   - Jarvis replies aloud and welcomes Alex.
3. **Test Conversational Memory**:
   > *"What is my name and how many messages have we exchanged?"*
   - Jarvis references the conversation history and confirms Alex's identity.
4. **Show Continuous Mode**:
   - Flip the **Continuous Mode** switch to demonstrate a completely hands-free voice dialogue loop.
5. **Show Live Waveform & Visual States**:
   - Point out the 4 visual feedback states: `READY` (idle blue), `LISTENING` (pulsing red orb), `THINKING` (spinning amber), and `SPEAKING` (purple wave glow).

---

## 🛠️ API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the Voice UI `index.html` |
| `POST` | `/chat` | Processes voice transcript, tracks history, returns AI reply |
| `GET` | `/history/{session_id}` | Retrieves conversation message history |
| `POST` | `/reset` | Clears conversation memory for a session |
| `GET` | `/health` | Health check & active session status |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## 📁 Project Structure

```
Jarvis/
├── main.py              # FastAPI server with /chat & conversation memory
├── index.html           # Voice-first UI (Web Speech + SpeechSynthesis)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template for OpenAI / Gemini keys
├── NOTES.md             # Development post-mortem & bug notes log
└── README.md            # Setup and live demo instructions
```
