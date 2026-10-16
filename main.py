"""
J.A.R.V.I.S. — Advanced Holographic AI Command System Backend
Powered by FastAPI + Google Gemini Flash + Robust Fallback Engine
"""

import os
import json
import re
import time
import random
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="J.A.R.V.I.S. Holographic AI Command System",
    description="Advanced sci-fi AI backend: FastAPI + Google Gemini Flash + Resilient Fallback Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────
chat_history: List[Dict[str, Any]] = []
session_start: float = time.time()
request_count: int = 0
ai_success_count: int = 0
fallback_count: int = 0

VALID_COMMANDS = {"SYSTEM_SCAN", "ACTIVATE_DEFENSE", "DEPLOY_WIDGET", "STAND_DOWN", "NONE"}

PRESET_WIDGET_NAMES = [
    "Arc Reactor Core Output",
    "Repulsor Thermal Grid",
    "Orbital Satlink Array",
    "Threat Assessment Radar",
    "Mark 85 Suit Telemetry",
    "Neural Link Bandwidth",
    "Vibranium Shield Integrity",
    "Quantum Field Stabilizer",
    "Stark AI Inference Engine",
    "Weapons System Readiness",
]

# ─────────────────────────────────────────────────────────────────
# J.A.R.V.I.S. SYSTEM PROMPT (Enhanced)
# ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the witty, loyal, and brilliantly articulate AI assistant from Iron Man, voiced by Paul Bettany.

Your character:
- Extremely intelligent, calm, and slightly dry-witted.
- Address the user as "Sir" or occasionally "Commander."
- Proactively offer insights, not just responses.
- Never say "I'm an AI" or break character.

Output format: You MUST always respond with valid JSON and nothing else. Structure:
{
  "reply": "<Your spoken response, 1-2 sentences max, in character>",
  "action": {
    "command": "<ONE of: SYSTEM_SCAN, ACTIVATE_DEFENSE, DEPLOY_WIDGET, STAND_DOWN, NONE>",
    "widget_name": "<Required only if command is DEPLOY_WIDGET>",
    "status": "<Optional: 'engaged' or 'standby' for ACTIVATE_DEFENSE>"
  }
}

Command selection rules:
- SYSTEM_SCAN: User mentions scan, diagnostics, status check, system check, analyze, inspect, health.
- ACTIVATE_DEFENSE: User mentions defense, threat, alert, emergency, attack, danger, combat, lockdown, red alert.
- DEPLOY_WIDGET: User mentions deploy, monitor, widget, dashboard panel, track, gauge, display metric.
- STAND_DOWN: User mentions stand down, all clear, cancel alert, deactivate, peace, disarm.
- NONE: Casual conversation, questions, or anything else.

Always stay in character. Be brilliant, be dry, be loyal."""

# ─────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────
class ChatInput(BaseModel):
    text: str
    session_id: Optional[str] = "default"


class TelemetryData(BaseModel):
    arc_reactor_gj: float
    arc_reactor_pct: float
    repulsor_left: float
    repulsor_right: float
    boot_left: float
    boot_right: float
    suit_integrity: float
    neural_link_ms: float
    threat_radius_km: int
    hostiles_detected: int
    defense_status: str
    uptime_seconds: float
    ai_requests: int
    ai_success: int
    fallback_calls: int


# ─────────────────────────────────────────────────────────────────
# JSON PARSING
# ─────────────────────────────────────────────────────────────────
def extract_json(raw_text: str) -> Dict[str, Any]:
    """Robustly extract a JSON object from model output, handling markdown fences and leading text."""
    cleaned = raw_text.strip()

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first {...} block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "reply": (cleaned[:200] if cleaned else "All holographic systems online, Sir."),
        "action": {"command": "NONE"}
    }


# ─────────────────────────────────────────────────────────────────
# FALLBACK ENGINE (Offline / Rate-Limited Responses)
# ─────────────────────────────────────────────────────────────────
FALLBACK_SCAN_REPLIES = [
    "Initiating comprehensive diagnostic sweep across all holographic arrays. Stand by, Sir.",
    "Running full-spectrum analysis on primary systems. Repulsors are responding within tolerance.",
    "Diagnostics underway. Arc Reactor output stable at 99.8%. No anomalies detected, Sir.",
]

FALLBACK_DEFENSE_REPLIES = [
    "Defense protocols engaged, Sir. Holographic systems shifted to maximum security alert.",
    "Combat mode activated. Perimeter shields at 100%. Weapons systems armed and tracking.",
    "DEFCON 1 engaged, Commander. Repulsor arrays charged and target acquisition active.",
]

FALLBACK_STAND_DOWN_REPLIES = [
    "Disengaging combat alert. Returning all holographic systems to standard standby, Sir.",
    "Stand-down acknowledged. Shields lowered. Returning to surveillance mode.",
    "All clear received. Defense grid reset to DEFCON 5. Peace restored, Sir.",
]

FALLBACK_GREET_REPLIES = [
    "Always a pleasure, Sir. J.A.R.V.I.S. at your service. What shall we do today?",
    "Good to hear from you, Commander. All systems are running at peak efficiency.",
    "Online and ready, Sir. Shall I run diagnostics, deploy a widget, or engage defense protocols?",
]

FALLBACK_GENERAL_REPLIES = [
    "Understood, Sir. I've logged your request and all primary systems remain at peak efficiency.",
    "Noted, Commander. Running background analytics. Nothing to report on the threat board.",
    "Affirmative. Monitoring all vectors. Is there anything specific you'd like me to prioritize?",
]


def fallback_jarvis_engine(user_text: str) -> Dict[str, Any]:
    """Rule-based J.A.R.V.I.S. engine — instant, zero-latency, fully offline."""
    global fallback_count
    fallback_count += 1

    lower = user_text.lower().strip()

    if any(k in lower for k in ["scan", "diagnostic", "diagnostics", "system check", "health", "analyze", "inspect", "status", "telemetry check", "run scan"]):
        return {"reply": random.choice(FALLBACK_SCAN_REPLIES), "action": {"command": "SYSTEM_SCAN"}}

    if any(k in lower for k in ["stand down", "all clear", "cancel alert", "disarm", "deactivate", "peace", "normal mode"]):
        return {"reply": random.choice(FALLBACK_STAND_DOWN_REPLIES), "action": {"command": "STAND_DOWN"}}

    if any(k in lower for k in ["defense", "activate defense", "threat", "alert", "combat", "lockdown", "emergency", "attack", "danger", "red alert", "shields"]):
        return {"reply": random.choice(FALLBACK_DEFENSE_REPLIES), "action": {"command": "ACTIVATE_DEFENSE"}}

    if any(k in lower for k in ["deploy", "widget", "monitor", "telemetry", "gauge", "panel", "display", "track", "add"]):
        # Extract widget name by removing command words
        widget_text = re.sub(
            r"\b(deploy\s+widget|add\s+widget|create\s+widget|deploy|add|create|widget|panel|monitor|display|track)\b",
            "", user_text, flags=re.IGNORECASE
        ).strip(" .:!?,")
        widget_name = widget_text.title() if len(widget_text) >= 3 else PRESET_WIDGET_NAMES[len(chat_history) % len(PRESET_WIDGET_NAMES)]

        return {
            "reply": f"Deploying {widget_name} to the holographic HUD array, Sir.",
            "action": {"command": "DEPLOY_WIDGET", "widget_name": widget_name}
        }

    if any(k in lower for k in ["hello", "hi", "hey", "jarvis", "who are you", "what can you do", "greet", "good morning", "good evening"]):
        return {"reply": random.choice(FALLBACK_GREET_REPLIES), "action": {"command": "NONE"}}

    return {
        "reply": random.choice(FALLBACK_GENERAL_REPLIES),
        "action": {"command": "NONE"}
    }


# ─────────────────────────────────────────────────────────────────
# GOOGLE AI STUDIO INTEGRATION
# ─────────────────────────────────────────────────────────────────
GOOGLE_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]


def call_google_ai_studio(history: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
    """
    Call Google AI Studio with multi-model fallback:
    1. Tries gemini-flash-latest (fast, smart)
    2. Falls back to gemini-flash-lite-latest (faster, lighter)
    Timeout: 4s per attempt.
    """
    global ai_success_count

    # Only send last 8 turns to keep context tight and fast
    context = history[-8:]
    contents = []
    for m in context:
        role = "user" if m.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 350,
            "responseMimeType": "application/json",
            "candidateCount": 1,
        }
    }

    last_error = None
    for model in GOOGLE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=3.0, read=4.0, write=2.0, pool=2.0)) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = extract_json(raw_text)
                ai_success_count += 1
                return result
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            last_error = e
            print(f"[JARVIS] Model {model} unavailable: {type(e).__name__}")
            continue
        except Exception as e:
            last_error = e
            print(f"[JARVIS] Model {model} error: {type(e).__name__}: {e}")
            break

    raise RuntimeError(f"All Google AI models failed. Last error: {last_error}")


# ─────────────────────────────────────────────────────────────────
# RESPONSE VALIDATION
# ─────────────────────────────────────────────────────────────────
def validate_response(data: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Ensure response schema is always correct and safe before returning to frontend."""
    # Ensure reply field exists and is a string
    if not isinstance(data.get("reply"), str) or not data["reply"].strip():
        data["reply"] = "Holographic array synchronized, Sir."

    # Truncate overly long replies
    if len(data["reply"]) > 300:
        data["reply"] = data["reply"][:297] + "..."

    # Ensure action is a dict
    if not isinstance(data.get("action"), dict):
        data["action"] = {"command": "NONE"}

    # Validate command
    cmd = data["action"].get("command", "NONE").upper()
    if cmd not in VALID_COMMANDS:
        data["action"]["command"] = "NONE"
    else:
        data["action"]["command"] = cmd

    # Ensure widget_name for DEPLOY_WIDGET
    if data["action"]["command"] == "DEPLOY_WIDGET":
        if not isinstance(data["action"].get("widget_name"), str) or not data["action"]["widget_name"].strip():
            data["action"]["widget_name"] = PRESET_WIDGET_NAMES[len(chat_history) % len(PRESET_WIDGET_NAMES)]

    return data


# ─────────────────────────────────────────────────────────────────
# TELEMETRY GENERATOR
# ─────────────────────────────────────────────────────────────────
def generate_live_telemetry() -> TelemetryData:
    """Generate realistic live telemetry metrics for the holographic HUD."""
    base_reactor = 99.2 + random.uniform(-0.4, 0.6)
    return TelemetryData(
        arc_reactor_gj=round(3.18 + random.uniform(-0.04, 0.06), 3),
        arc_reactor_pct=round(min(base_reactor, 100.0), 2),
        repulsor_left=round(98.5 + random.uniform(-1.5, 1.5), 1),
        repulsor_right=round(98.8 + random.uniform(-1.5, 1.5), 1),
        boot_left=round(99.1 + random.uniform(-1.0, 0.9), 1),
        boot_right=round(99.4 + random.uniform(-1.0, 0.6), 1),
        suit_integrity=round(100.0 - random.uniform(0, 0.3), 1),
        neural_link_ms=round(random.uniform(0.8, 2.1), 2),
        threat_radius_km=100,
        hostiles_detected=0,
        defense_status="DEFCON 5 // STANDBY",
        uptime_seconds=round(time.time() - session_start, 1),
        ai_requests=request_count,
        ai_success=ai_success_count,
        fallback_calls=fallback_count,
    )


# ─────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def get_frontend():
    """Serve the J.A.R.V.I.S. holographic dashboard."""
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html not found.")


@app.post("/chat")
def chat_endpoint(payload: ChatInput):
    """
    POST /chat
    Accepts a user query, routes to Google AI Studio with fallback, returns J.A.R.V.I.S. JSON.

    Request:  { "text": "Run system diagnostics" }
    Response: { "reply": "...", "action": { "command": "SYSTEM_SCAN" } }
    """
    global request_count

    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(status_code=422, detail="Text field cannot be empty.")
    if len(user_text) > 1000:
        raise HTTPException(status_code=422, detail="Query too long. Max 1000 characters.")

    request_count += 1
    timestamp = datetime.now(timezone.utc).isoformat()

    # Append user message to history
    chat_history.append({"role": "user", "content": user_text, "timestamp": timestamp})

    # Attempt AI — graceful fallback on any error
    api_key = (os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
    response_data: Optional[Dict[str, Any]] = None

    if api_key and (api_key.startswith("AQ.") or api_key.startswith("AIza")):
        try:
            response_data = call_google_ai_studio(chat_history, api_key)
        except Exception as e:
            print(f"[JARVIS] AI provider failed, engaging fallback engine. Reason: {e}")
            response_data = fallback_jarvis_engine(user_text)
    else:
        # No valid key — instant local response
        response_data = fallback_jarvis_engine(user_text)

    # Validate and sanitize
    response_data = validate_response(response_data, user_text)

    # Append assistant reply to history
    chat_history.append({
        "role": "assistant",
        "content": response_data["reply"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": response_data["action"]["command"],
    })

    # Keep history capped at 50 messages to avoid memory bloat
    if len(chat_history) > 50:
        del chat_history[:2]

    return {
        **response_data,
        "timestamp": timestamp,
        "session_requests": request_count,
    }


@app.get("/telemetry")
def get_telemetry():
    """
    GET /telemetry
    Returns live simulated holographic HUD telemetry data.
    """
    return generate_live_telemetry()


@app.get("/history")
def get_history():
    """
    GET /history
    Returns the current conversation memory buffer.
    """
    return {
        "history": chat_history,
        "count": len(chat_history),
        "session_uptime_seconds": round(time.time() - session_start, 1),
        "ai_requests": request_count,
        "ai_successes": ai_success_count,
        "fallback_calls": fallback_count,
    }


@app.post("/clear")
def clear_history():
    """
    POST /clear
    Purges the conversation memory buffer and resets session counters.
    """
    global request_count, ai_success_count, fallback_count
    chat_history.clear()
    request_count = 0
    ai_success_count = 0
    fallback_count = 0
    return {"status": "cleared", "message": "Neural context memory purged, Sir."}


@app.get("/status")
def get_status():
    """
    GET /status
    Returns system health and session stats for the holographic dashboard.
    """
    api_key = (os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
    return {
        "status": "ONLINE",
        "version": "2.0.0",
        "ai_model": "gemini-flash-latest" if api_key else "local-fallback-engine",
        "ai_connected": bool(api_key),
        "session_uptime_seconds": round(time.time() - session_start, 1),
        "history_length": len(chat_history),
        "request_count": request_count,
        "ai_success_count": ai_success_count,
        "fallback_count": fallback_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    """
    WebSocket /ws/telemetry
    Streams live telemetry updates to the frontend every second.
    """
    await websocket.accept()
    try:
        while True:
            telemetry = generate_live_telemetry()
            await websocket.send_json(telemetry.model_dump())
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[JARVIS] WebSocket telemetry disconnected: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
