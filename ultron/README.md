# ⚡ Ultron — Free Open-Source Local Desktop Automation Agent

Ultron is a modular, production-grade local desktop automation agent that executes natural language instructions (file management, system vision, and keyboard/mouse automation) using 100% free-tier AI models (Ollama, Groq, or Google AI Studio).

---

## 📁 Project Architecture

```
ultron/
├── .env                  # Local environment configuration (ignored by git)
├── .env.example          # Template with free-tier LLM key placeholders
├── .gitignore            # Excludes secrets, logs, screenshots, and caches
├── requirements.txt      # Core dependencies (pyautogui, pillow, groq, etc.)
├── brain.py              # AI reasoning engine & structured JSON command generator
├── main.py               # Interactive CLI runner loop & safe execution dispatcher
└── tools/
    ├── __init__.py       # Centralized tool registry and LLM catalog schemas
    ├── file_manager.py   # Defensive folder/file creation, deletion, listing, moving
    ├── vision.py         # Timestamped desktop screenshot capture (Pillow + native)
    └── automation.py     # Safe PyAutoGUI keyboard, mouse, app, and messaging wrappers
```

---

## 🚀 Quickstart Guide

### 1. (Recommended) Open as Standalone Workspace
You can open this folder directly in Antigravity or VS Code:
```bash
# In your terminal:
code /path/to/ultron
# Or in Antigravity: File > Open Folder... -> select "ultron"
```

### 2. Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Your Free LLM
Edit `.env` and set your preferred free inference provider:
- **Groq (Free & Fast)**: Set `GROQ_API_KEY` from [console.groq.com](https://console.groq.com)
- **Google AI Studio (Free Gemini)**: Set `GEMINI_API_KEY` from [aistudio.google.com](https://aistudio.google.com)
- **Ollama (100% Free Local Offline)**: Run `ollama run llama3.2` (no keys needed!)

### 4. Run Ultron

**Interactive Mode:**
```bash
python main.py
```

**Single Command Mode:**
```bash
python main.py "take a screenshot of my screen"
python main.py "create a folder called ProjectX on my desktop"
python main.py "list files on my desktop"
```

---

## 🛡️ Built-in Safety Guardrails
- **PyAutoGUI Failsafe**: Move your mouse cursor to any screen corner to abort mouse actions immediately.
- **Mandatory Safe Pause**: 0.5s pause between automation steps.
- **Confirmation Prompts**: Destructive file deletions and messaging prompt for confirmation unless safe mode is disabled.
- **Path Traversal Defense**: Prevents modifying or deleting critical system root folders.
