import os
import json
import re
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="J.A.R.V.I.S. Holographic AI System Dashboard",
    description="Advanced sci-fi AI assistant backend powered by FastAPI and Google Gemma 4"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global chat history list to store context
chat_history: List[Dict[str, str]] = []

# Upgraded J.A.R.V.I.S. System Prompt
SYSTEM_PROMPT = (
    "You are an advanced, witty AI system assistant operating a holographic dashboard, similar to Jarvis from Iron Man. "
    "Keep responses concise, intelligent, and slightly dry. Always respond in valid JSON with two keys: 'reply' "
    "(your spoken text) and 'action'. The 'action' key must be an object with a 'command' field. Available commands: \n"
    "  - SYSTEM_SCAN (simulates running diagnostics)\n"
    "  - ACTIVATE_DEFENSE (turns the UI red/alert mode)\n"
    "  - DEPLOY_WIDGET (adds a data widget to the screen with a 'widget_name' field)\n"
    "  - NONE (just chatting)."
)

class ChatInput(BaseModel):
    text: str


def extract_json(raw_text: str) -> Dict[str, Any]:
    """Parse JSON from model response, handling optional markdown code fences."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "reply": raw_text.replace("{", "").replace("}", "").strip() or "All holographic systems online, Sir.",
        "action": {"command": "NONE"}
    }


def fallback_jarvis_engine(user_text: str) -> Dict[str, Any]:
    """Rule-based J.A.R.V.I.S. engine ensuring instant offline operation with full persona."""
    lower = user_text.lower().strip()

    # 1. SYSTEM_SCAN (simulates running diagnostics)
    if any(k in lower for k in ["scan", "diagnostic", "diagnostics", "check systems", "system check", "run scan", "status report", "telemetry check"]):
        return {
            "reply": "Initiating comprehensive diagnostic scan across all holographic arrays. Stand by, Sir.",
            "action": {"command": "SYSTEM_SCAN"}
        }

    # 2. ACTIVATE_DEFENSE (turns UI red / alert mode)
    if any(k in lower for k in [
        "defense", "activate defense", "defense protocol", "alert mode", "red alert",
        "shields up", "threat detected", "combat mode", "lockdown", "emergency", "defend"
    ]):
        return {
            "reply": "Defense protocols engaged, Sir. Switching holographic systems to maximum security alert.",
            "action": {"command": "ACTIVATE_DEFENSE"}
        }

    # 3. DEPLOY_WIDGET (adds a data widget to the screen with widget_name)
    if any(k in lower for k in ["deploy widget", "add widget", "widget", "deploy", "monitor", "telemetry", "gauge", "panel"]):
        # Extract meaningful widget title
        cleaned = re.sub(r"(?i)\b(deploy\s+widget|add\s+widget|create\s+widget|deploy|add|create|widget|panel|monitor)\b", "", user_text).strip(" .:!?,")
        widget_name = cleaned.title() if cleaned else "Arc Reactor Telemetry"

        # Preset stylish fallback names if generic
        if len(widget_name) < 3 or widget_name.lower() in ["widget", "a widget", "new"]:
            preset_names = [
                "Arc Reactor Output",
                "Repulsor Core Thermal Grid",
                "Orbital Satlink Uplink",
                "Threat Assessment Radar",
                "Mark 85 Suit Telemetry",
                "Clean Energy Microgrid"
            ]
            widget_name = preset_names[len(chat_history) % len(preset_names)]

        return {
            "reply": f"Deploying {widget_name} to the holographic HUD array, Sir.",
            "action": {
                "command": "DEPLOY_WIDGET",
                "widget_name": widget_name
            }
        }

    # 4. Stand down / normal mode
    if any(k in lower for k in ["stand down", "cancel alert", "deactivate defense", "normal mode", "all clear"]):
        return {
            "reply": "Disengaging combat alert status. Returning holographic systems to standard standby, Sir.",
            "action": {"command": "ACTIVATE_DEFENSE", "status": "standby"}
        }

    # 5. Conversational witty British replies (NONE)
    if any(k in lower for k in ["hello", "hi", "hey", "jarvis", "who are you", "what can you do"]):
        return {
            "reply": "Always a pleasure, Sir. J.A.R.V.I.S. at your service. Tell me to run diagnostics, deploy widgets, or engage defense protocols.",
            "action": {"command": "NONE"}
        }

    return {
        "reply": f"Understood, Sir. Monitoring '{user_text}'. All primary systems remain at peak efficiency.",
        "action": {"command": "NONE"}
    }


def call_google_ai_studio(history: List[Dict[str, str]], api_key: str) -> Dict[str, Any]:
    """Call Google AI Studio endpoint with strict 2.0s timeout to guarantee instant UI responses."""
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

    contents = []
    for m in history[-6:]:
        role = "user" if m.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300, "responseMimeType": "application/json"}
    }

    with httpx.Client(timeout=2.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        res = resp.json()
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"]
        return extract_json(raw_text)


@app.get("/")
def get_frontend():
    """Serve index.html at root."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "index.html not found"}


@app.post("/chat")
def chat_endpoint(payload: ChatInput):
    """
    POST /chat endpoint:
    - Appends user text to chat_history.
    - Connects to Google AI Studio (Gemma/Gemini) or Hugging Face.
    - Parses structured JSON response.
    - Appends assistant reply to history and returns JSON.
    """
    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # 1. Append user text to conversational context
    chat_history.append({"role": "user", "content": user_text})

    # Read GEMMA_API_KEY from environment
    api_key = os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN")
    response_data = None

    # 2. Call AI provider if key is configured
    if api_key:
        api_key_clean = api_key.strip()
        try:
            # Check for Google AI Studio key format (starts with AQ. or AIza)
            if api_key_clean.startswith("AQ.") or api_key_clean.startswith("AIza"):
                response_data = call_google_ai_studio(chat_history, api_key_clean)
            # Check for Hugging Face token format (starts with hf_)
            elif api_key_clean.startswith("hf_"):
                client = InferenceClient(token=api_key_clean)
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(chat_history)
                response = client.chat_completion(
                    model="google/gemma-4-instruct",
                    messages=messages,
                    max_tokens=250,
                    temperature=0.2
                )
                raw_reply = response.choices[0].message.content
                response_data = extract_json(raw_reply)
            else:
                # Try Google first, fall back to Hugging Face
                try:
                    response_data = call_google_ai_studio(chat_history, api_key_clean)
                except Exception:
                    client = InferenceClient(token=api_key_clean)
                    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                    messages.extend(chat_history)
                    response = client.chat_completion(
                        model="google/gemma-4-instruct",
                        messages=messages,
                        max_tokens=250,
                        temperature=0.2
                    )
                    raw_reply = response.choices[0].message.content
                    response_data = extract_json(raw_reply)

        except Exception as e:
            print(f"[AI Provider Warning]: {e}")
            response_data = fallback_jarvis_engine(user_text)
    else:
        # Fast local fallback ensuring immediate offline functionality
        response_data = fallback_jarvis_engine(user_text)

    # Validate action object and command
    if not isinstance(response_data.get("action"), dict):
        response_data["action"] = {"command": "NONE"}

    valid_commands = {"SYSTEM_SCAN", "ACTIVATE_DEFENSE", "DEPLOY_WIDGET", "NONE"}
    cmd = response_data["action"].get("command")
    if cmd not in valid_commands:
        response_data["action"]["command"] = "NONE"

    if cmd == "DEPLOY_WIDGET" and not response_data["action"].get("widget_name"):
        response_data["action"]["widget_name"] = "Telemetry Sensor Grid"

    if "reply" not in response_data:
        response_data["reply"] = "Holographic array synchronized, Sir."

    # 3. Append assistant reply to conversational context
    chat_history.append({"role": "assistant", "content": response_data["reply"]})

    # 4. Return structured JSON
    return response_data


@app.get("/history")
def get_history():
    """Retrieve chat history."""
    return {"history": chat_history, "count": len(chat_history)}


@app.post("/clear")
def clear_history():
    """Clear chat history."""
    global chat_history
    chat_history.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
