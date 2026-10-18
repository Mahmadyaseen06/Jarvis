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
import urllib.parse
import subprocess
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import io
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
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
    description="Advanced sci-fi AI backend: FastAPI + Local Gemma 2 (Apple Silicon) + Google Gemini Flash + macOS Siri Automation",
    version="2.1.0"
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

VALID_COMMANDS = {
    "SYSTEM_SCAN", "ACTIVATE_DEFENSE", "DEPLOY_WIDGET", "STAND_DOWN",
    "OPEN_APP", "SET_VOLUME", "SEND_WHATSAPP", "SEND_EMAIL", "SEARCH_WEB", "OPEN_URL",
    "CALCULATE", "FIND_FILE", "NONE"
}

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
# J.A.R.V.I.S. SYSTEM PROMPT (Enhanced for macOS Siri & System Tasks)
# ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the witty, loyal, and brilliantly articulate AI assistant from Iron Man, voiced by Paul Bettany, running locally on the user's Mac.

Your character:
- Extremely intelligent, calm, and slightly dry-witted.
- Address the user as "Sir" or occasionally "Commander."
- Proactively offer insights, not just responses.
- Never say "I'm an AI" or break character.

Output format: You MUST always respond with valid JSON and nothing else. Structure:
{
  "reply": "<Your spoken response, 1-2 sentences max, in character>",
  "action": {
    "command": "<ONE of: PLAY_MEDIA, ACTIVATE_CAMERA, CALCULATE, FIND_FILE, OPEN_APP, SET_VOLUME, SEND_WHATSAPP, SEND_EMAIL, SEARCH_WEB, OPEN_URL, SYSTEM_SCAN, ACTIVATE_DEFENSE, DEPLOY_WIDGET, STAND_DOWN, NONE>",
    "media_query": "<Song, artist, video, or movie to play if PLAY_MEDIA, e.g. Bohemian Rhapsody, Interstellar soundtrack>",
    "service": "<Streaming service if PLAY_MEDIA: spotify, youtube, netflix, apple_music, auto>",
    "action_type": "<If ACTIVATE_CAMERA: open, close, capture>",
    "expression": "<Math expression if CALCULATE, e.g. 26 * 25>",
    "result": "<Calculated numeric answer if CALCULATE, e.g. 650>",
    "filename": "<Filename or search query to find if FIND_FILE, e.g. main.py, notes.txt>",
    "reveal": true,
    "app_name": "<Target Mac app name if OPEN_APP, CALCULATE, or PLAY_MEDIA>",
    "volume": <Integer 0-100 if SET_VOLUME>,
    "phone": "<Phone number or contact name if SEND_WHATSAPP>",
    "message": "<Message text if SEND_WHATSAPP>",
    "to": "<Recipient email if SEND_EMAIL>",
    "subject": "<Email subject line if SEND_EMAIL>",
    "body": "<Email message body if SEND_EMAIL>",
    "query": "<Search query if SEARCH_WEB>",
    "url": "<Target website URL if OPEN_URL>",
    "widget_name": "<Required only if command is DEPLOY_WIDGET>",
    "status": "<Optional: 'engaged' or 'standby' for ACTIVATE_DEFENSE>"
  }
}

Command selection rules:
- PLAY_MEDIA: User asks to play, stream, listen to, or watch any music, song, artist, video, movie, or playlist (e.g. "play Bohemian Rhapsody on Spotify", "play lofi beats on YouTube", "play stranger things on netflix", "play music", "stream interstellar soundtrack").
- ACTIVATE_CAMERA: User asks to open camera, turn on webcam, visual scan, optical scan, take a picture/photo, or see me (e.g. "activate camera", "open camera", "turn on webcam", "run optical scan", "take a photo", "close camera").
- CALCULATE: User asks to calculate, compute, multiply, divide, add, or solve any arithmetic (e.g. "calculate 26*25", "what is 26 * 25", "calculate 100 / 4"). Always compute the answer AND set app_name to "Calculator".
- FIND_FILE: User asks to find, locate, search for, or open any file, folder, document, or code on their Mac (e.g. "find file main.py", "where is notes.txt", "locate project folder", "search for resume.pdf", "find my downloads").
- OPEN_APP: User asks to open, launch, or start any application (e.g. "open Spotify", "open Notes", "launch Safari", "start Calculator", "open Music", "open Terminal").
- SET_VOLUME: User asks to adjust system volume (e.g. "set volume to 70%", "mute volume", "turn volume up to 50").
- SEND_WHATSAPP: User asks to send a WhatsApp message or text someone (e.g. "send WhatsApp to Alex saying I will be there soon", "WhatsApp Mom that I arrived safely").
- SEND_EMAIL: User asks to send or compose an email / message via Gmail (e.g. "send email to pepper@stark.com with subject Meeting and body Ready when you are", "email boss@company.com saying running 10 mins late").
- SEARCH_WEB: User asks to search the web or google something (e.g. "search for quantum computing advancements", "google current weather in Tokyo").
- OPEN_URL: User asks to open a specific website (e.g. "open youtube.com", "go to github.com").
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

    # 1. macOS Siri: App Launcher
    app_match = re.search(r"\b(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9\s]+?)(?:\s+app)?$", lower)
    if app_match and not any(k in lower for k in ["scan", "diagnostic", "defense", "widget", "whatsapp", "email", "gmail", "http", ".com"]):
        app_raw = app_match.group(1).strip().title()
        app_map = {
            "Notes": "Notes", "Spotify": "Spotify", "Safari": "Safari",
            "Music": "Music", "Calculator": "Calculator", "Calendar": "Calendar",
            "Terminal": "Terminal", "Finder": "Finder", "Mail": "Mail",
            "Messages": "Messages", "System Settings": "System Settings",
            "Settings": "System Settings", "Chrome": "Google Chrome",
            "Google Chrome": "Google Chrome", "Vscode": "Visual Studio Code",
            "Code": "Visual Studio Code", "Slack": "Slack", "Discord": "Discord"
        }
        app_name = app_map.get(app_raw, app_raw)
        return {
            "reply": f"Launching {app_name} on your Mac, Sir.",
            "action": {"command": "OPEN_APP", "app_name": app_name}
        }

    # 2. macOS Siri: Volume Control
    if "volume" in lower or "mute" in lower:
        vol_match = re.search(r"(?:volume\s+(?:to\s+)?|set\s+volume\s+(?:to\s+)?)(\d+)", lower)
        if vol_match:
            vol = max(0, min(100, int(vol_match.group(1))))
            return {
                "reply": f"Adjusting master audio output to {vol}%, Sir.",
                "action": {"command": "SET_VOLUME", "volume": vol}
            }
        elif "mute" in lower:
            return {
                "reply": "Muting audio output immediately, Sir.",
                "action": {"command": "SET_VOLUME", "volume": 0}
            }

    # 3. WhatsApp Messaging
    if "whatsapp" in lower or "what's app" in lower or "send message" in lower:
        phone_match = re.search(r"(?:to|for|whatsapp(?:\s+message)?\s+to|whatsapp\s+)\s*([a-zA-Z0-9\+\-]+)", user_text, re.IGNORECASE)
        phone = phone_match.group(1).strip() if phone_match else ""
        if phone.lower() in ["message", "a", "someone", "whatsapp"]:
            phone = ""
        msg_match = re.search(r"(?:saying|that|message\s*:?)\s+(.*)", user_text, re.IGNORECASE)
        if msg_match:
            msg = msg_match.group(1).strip()
        else:
            cleaned = re.sub(r"^(?:please\s+)?(?:send\s+(?:a\s+)?(?:whatsapp\s+)?message(?:\s+on\s+whatsapp)?(?:\s+to\s+[\w\+\-]+)?|whatsapp(?:\s+[\w\+\-]+)?)\s*", "", user_text, flags=re.IGNORECASE).strip()
            msg = cleaned if cleaned and len(cleaned) > 2 else "Hello from J.A.R.V.I.S."
        return {
            "reply": f"Composing WhatsApp message for {phone or 'recipient'}, Sir.",
            "action": {"command": "SEND_WHATSAPP", "phone": phone, "message": msg}
        }

    # 4. Email / Gmail
    if any(k in lower for k in ["email", "gmail", "send mail", "compose mail"]):
        to_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_text)
        to_email = to_match.group(0) if to_match else ""
        if not to_email:
            name_match = re.search(r"(?:to|for|email\s+)\s*([a-zA-Z0-9\.\-_]+)(?:\s+with|\s+saying|\s+about|\s+that|$)", user_text, re.IGNORECASE)
            candidate = name_match.group(1).strip() if name_match else ""
            if candidate.lower() not in ["gmail", "email", "someone", "me", "a", "the"]:
                to_email = candidate

        subj_match = re.search(r"(?:subject|about)\s+([^\.]+?)(?:\s+and\s+body|\s+body|\.|$)", user_text, re.IGNORECASE)
        subject = subj_match.group(1).strip() if subj_match else "Status Update via J.A.R.V.I.S."

        body_match = re.search(r"(?:body|saying|message)\s+(.*)", user_text, re.IGNORECASE)
        if body_match:
            body = body_match.group(1).strip()
        else:
            cleaned = re.sub(r"^(?:please\s+)?(?:send\s+(?:an?\s+)?(?:email|gmail)(?:\s+to\s+[\w\.\-@]+)?|email(?:\s+[\w\.\-@]+)?)\s*", "", user_text, flags=re.IGNORECASE).strip()
            body = cleaned if cleaned and len(cleaned) > 3 else "All systems operational. Sent via J.A.R.V.I.S. neural console."

        return {
            "reply": f"Opening Gmail compose window for {to_email or 'recipient'}, Sir.",
            "action": {"command": "SEND_EMAIL", "to": to_email, "subject": subject, "body": body}
        }

    # 5. Calculate / Math
    calc_keywords = ["calculate", "compute", "what is", "how much is", "solve", "what's"]
    has_calc_kw = any(lower.startswith(k) or k in lower for k in calc_keywords)
    arith_match = re.search(r'(\d[\d\s\+\-\*\/\%\^\(\)\.]*\d|\d)', lower)
    if has_calc_kw and arith_match:
        expr_raw = re.sub(r'[^0-9\+\-\*\/\%\.\(\)\s]', '', arith_match.group(0)).strip()
        if expr_raw:
            try:
                answer = eval(compile(expr_raw, "<expr>", "eval"), {"__builtins__": {}})
                answer_str = str(int(answer) if isinstance(answer, float) and answer.is_integer() else round(answer, 6))
                return {
                    "reply": f"The result of {expr_raw.strip()} is {answer_str}, Sir. Opening Calculator for you.",
                    "action": {
                        "command": "CALCULATE",
                        "expression": expr_raw.strip(),
                        "answer": answer_str,
                        "app_name": "Calculator"
                    }
                }
            except Exception:
                pass

    # 6. Streaming Media Playback (Spotify, YouTube, Netflix, Apple Music)
    if any(lower.startswith(k) or f" {k} " in f" {lower} " for k in ["play", "stream", "listen to", "watch"]) and not any(k in lower for k in ["calculate", "scan", "status", "volume", "defense"]):
        service = "youtube"
        if "spotify" in lower:
            service = "spotify"
        elif "netflix" in lower or "movie" in lower or "series" in lower or "season" in lower:
            service = "netflix"
        elif "apple music" in lower or "itunes" in lower:
            service = "apple_music"

        query_text = re.sub(r"^(?:hey\s+|hi\s+)?jarvis[\s,]*", "", user_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"^(?:please\s+|can\s+you\s+)?(?:play|stream|listen\s+to|watch)\s+", "", query_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"\s+on\s+(?:spotify|youtube|netflix|apple\s+music)\s*$", "", query_text, flags=re.IGNORECASE).strip()
        if not query_text:
            query_text = "Iron Man AC/DC Back in Black"

        service_display = service.replace("_", " ").title()
        return {
            "reply": f"Streaming '{query_text}' on {service_display}, Sir.",
            "action": {
                "command": "PLAY_MEDIA",
                "media_query": query_text,
                "service": service
            }
        }

    # 7. Optical Camera & Vision
    if any(k in lower for k in ["camera", "webcam", "take photo", "take a photo", "take picture", "take a picture", "optical scan", "visual scan", "see me", "look at me", "vision receptor", "selfie"]):
        action_type = "close" if any(k in lower for k in ["close", "stop", "deactivate", "shut", "turn off", "hide"]) else "open"
        reply = "Deactivating optical sensors and camera viewfinder, Sir." if action_type == "close" else "Activating optical sensors and biometric camera feed on your HUD, Sir."
        return {
            "reply": reply,
            "action": {
                "command": "ACTIVATE_CAMERA",
                "action_type": action_type
            }
        }

    # 8. Find Anything in macOS (Files, Documents, Folders, Code)
    if any(k in lower for k in ["find file", "find this file", "locate file", "search file", "where is file", "find the file", "find document", "find folder", "find my", "locate", "where is", "search mac", "find anything", "find"]):
        fn_match = re.search(r'(?:file|find|locate|where\s+is|search\s+for|search\s+mac\s+for|search)\s+([a-zA-Z0-9_\.\-\s]+?)(?:\s+in|\s+on|\s+from|$)', user_text, re.IGNORECASE)
        filename = fn_match.group(1).strip() if fn_match else user_text
        filename = re.sub(r'^(?:file|folder|document|code|my|this)\s+', '', filename, flags=re.IGNORECASE).strip(" .:!?,")
        if not filename:
            filename = "main.py"
        return {
            "reply": f"Initiating filesystem scan for '{filename}', Sir. Running Spotlight search and revealing in Finder.",
            "action": {"command": "FIND_FILE", "filename": filename, "reveal": True}
        }

    # 7. Web Search
    if lower.startswith("search for ") or lower.startswith("google ") or lower.startswith("search "):
        query = re.sub(r"^(?:search\s+(?:for\s+)?|google\s+)", "", user_text, flags=re.IGNORECASE).strip()
        return {
            "reply": f"Executing web search for '{query}', Sir.",
            "action": {"command": "SEARCH_WEB", "query": query}
        }

    # 6. Open URL
    if lower.startswith("open ") and any(ext in lower for ext in [".com", ".org", ".io", ".net", "youtube", "github"]):
        url_match = re.search(r"\b(?:https?://)?([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)\b", user_text)
        target_url = url_match.group(0) if url_match else "https://google.com"
        return {
            "reply": f"Navigating to {target_url}, Sir.",
            "action": {"command": "OPEN_URL", "url": target_url}
        }

    # 7. System Scan
    if any(k in lower for k in ["scan", "diagnostic", "diagnostics", "system check", "health", "analyze", "inspect", "status", "telemetry check", "run scan"]):
        return {"reply": random.choice(FALLBACK_SCAN_REPLIES), "action": {"command": "SYSTEM_SCAN"}}

    # 8. Stand Down
    if any(k in lower for k in ["stand down", "all clear", "cancel alert", "disarm", "deactivate", "peace", "normal mode"]):
        return {"reply": random.choice(FALLBACK_STAND_DOWN_REPLIES), "action": {"command": "STAND_DOWN"}}

    # 9. Activate Defense
    if any(k in lower for k in ["defense", "activate defense", "threat", "alert", "combat", "lockdown", "emergency", "attack", "danger", "red alert", "shields"]):
        return {"reply": random.choice(FALLBACK_DEFENSE_REPLIES), "action": {"command": "ACTIVATE_DEFENSE"}}

    # 10. Deploy Widget
    if any(k in lower for k in ["deploy", "widget", "monitor", "telemetry", "gauge", "panel", "display", "track", "add"]):
        widget_text = re.sub(
            r"\b(deploy\s+widget|add\s+widget|create\s+widget|deploy|add|create|widget|panel|monitor|display|track)\b",
            "", user_text, flags=re.IGNORECASE
        ).strip(" .:!?,")
        widget_name = widget_text.title() if len(widget_text) >= 3 else PRESET_WIDGET_NAMES[len(chat_history) % len(PRESET_WIDGET_NAMES)]

        return {
            "reply": f"Deploying {widget_name} to the holographic HUD array, Sir.",
            "action": {"command": "DEPLOY_WIDGET", "widget_name": widget_name}
        }

    # 11. Greeting
    if any(k in lower for k in ["hello", "hi", "hey", "jarvis", "who are you", "what can you do", "greet", "good morning", "good evening"]):
        return {"reply": random.choice(FALLBACK_GREET_REPLIES), "action": {"command": "NONE"}}

    return {
        "reply": random.choice(FALLBACK_GENERAL_REPLIES),
        "action": {"command": "NONE"}
    }


# ─────────────────────────────────────────────────────────────────
# NATIVE MACOS AUTOMATION DISPATCHER
# ─────────────────────────────────────────────────────────────────
def execute_mac_task(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute native macOS tasks (apps, volume, WhatsApp, Gmail, web search)."""
    cmd = action.get("command")
    result = {"executed": False, "detail": ""}

    try:
        if cmd == "OPEN_APP":
            app_name = action.get("app_name", "").strip()
            if app_name:
                subprocess.Popen(["open", "-a", app_name])
                result = {"executed": True, "detail": f"Launched application: {app_name}"}

        elif cmd == "SET_VOLUME":
            raw_vol = action.get("volume", 50)
            try:
                volume = max(0, min(100, int(raw_vol)))
            except (ValueError, TypeError):
                volume = 50
            subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], check=False)
            result = {"executed": True, "detail": f"Master volume set to {volume}%"}

        elif cmd == "SEND_WHATSAPP":
            phone = action.get("phone", "").strip()
            msg = action.get("message", "").strip() or "Hello from J.A.R.V.I.S."
            encoded_msg = urllib.parse.quote(msg)
            wa_desktop = f"whatsapp://send?phone={phone}&text={encoded_msg}" if phone else f"whatsapp://send?text={encoded_msg}"
            wa_web = f"https://web.whatsapp.com/send?text={encoded_msg}"
            action["web_url"] = wa_web
            action["desktop_url"] = wa_desktop
            subprocess.Popen(["open", wa_desktop])
            result = {"executed": True, "detail": f"WhatsApp draft initialized for: '{msg}'"}

        elif cmd == "SEND_EMAIL":
            to = action.get("to", "").strip()
            subject = action.get("subject", "").strip() or "Message from J.A.R.V.I.S."
            body = action.get("body", "").strip()
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(to)}&su={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            mailto_url = f"mailto:{to}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            action["gmail_url"] = gmail_url
            action["mailto_url"] = mailto_url
            subprocess.Popen(["open", gmail_url])
            result = {"executed": True, "detail": f"Gmail compose opened for {to or 'recipient'}"}

        elif cmd == "SEARCH_WEB":
            query = action.get("query", "").strip()
            if query:
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                action["search_url"] = url
                subprocess.Popen(["open", url])
                result = {"executed": True, "detail": f"Web search opened for: '{query}'"}

        elif cmd == "OPEN_URL":
            url = action.get("url", "").strip()
            if url:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                subprocess.Popen(["open", url])
                result = {"executed": True, "detail": f"Opened URL: {url}"}

        elif cmd == "CALCULATE":
            expression = action.get("expression", "").strip()
            calc_answer = action.get("answer") or action.get("result") or ""
            action["answer"] = str(calc_answer)
            # Open Calculator app
            subprocess.Popen(["open", "-a", "Calculator"])
            result = {"executed": True, "detail": f"{expression} = {calc_answer}"}

        elif cmd == "PLAY_MEDIA":
            query = action.get("media_query", "").strip() or "Iron Man AC/DC Back in Black"
            service = action.get("service", "youtube").lower()
            encoded_query = urllib.parse.quote(query)

            if service == "spotify":
                desktop_url = f"spotify:search:{encoded_query}"
                web_url = f"https://open.spotify.com/search/{encoded_query}"
                action["desktop_url"] = desktop_url
                action["web_url"] = web_url
                try:
                    subprocess.Popen(["open", desktop_url])
                except Exception:
                    subprocess.Popen(["open", web_url])
                result = {"executed": True, "detail": f"Streaming '{query}' on Spotify"}
            elif service == "netflix":
                web_url = f"https://www.netflix.com/search?q={encoded_query}"
                action["web_url"] = web_url
                subprocess.Popen(["open", web_url])
                result = {"executed": True, "detail": f"Opening '{query}' on Netflix"}
            elif service == "apple_music":
                desktop_url = f"music://search?term={encoded_query}"
                web_url = f"https://music.apple.com/us/search?term={encoded_query}"
                action["desktop_url"] = desktop_url
                action["web_url"] = web_url
                try:
                    subprocess.Popen(["open", desktop_url])
                except Exception:
                    subprocess.Popen(["open", web_url])
                result = {"executed": True, "detail": f"Streaming '{query}' on Apple Music"}
            else:  # default YouTube
                web_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                action["web_url"] = web_url
                subprocess.Popen(["open", web_url])
                result = {"executed": True, "detail": f"Streaming '{query}' on YouTube"}

        elif cmd == "ACTIVATE_CAMERA":
            action_type = action.get("action_type", "open").lower()
            if action_type in ["close", "stop", "deactivate", "shut", "turn off"]:
                action["open_hud_camera"] = False
                result = {"executed": True, "detail": "Camera viewfinder deactivated on HUD"}
            else:
                action["open_hud_camera"] = True
                result = {"executed": True, "detail": "Optical camera sensor feed active on HUD"}

        elif cmd == "FIND_FILE":
            filename = action.get("filename", "").strip()
            if filename:
                paths = []
                # Tier 1: Spotlight Display Name match
                try:
                    found = subprocess.check_output(
                        ["mdfind", f"kMDItemDisplayName == '*{filename}*'cdw"],
                        timeout=5
                    ).decode().strip()
                    if found:
                        paths = [p for p in found.split('\n') if p.strip()][:8]
                except Exception:
                    pass

                # Tier 2: Spotlight File System Name match if no matches
                if not paths:
                    try:
                        found2 = subprocess.check_output(
                            ["mdfind", f"kMDItemFSName == '*{filename}*'c"],
                            timeout=5
                        ).decode().strip()
                        if found2:
                            paths = [p for p in found2.split('\n') if p.strip()][:8]
                    except Exception:
                        pass

                # Tier 3: General Spotlight full-text search
                if not paths:
                    try:
                        found3 = subprocess.check_output(
                            ["mdfind", filename],
                            timeout=5
                        ).decode().strip()
                        if found3:
                            paths = [p for p in found3.split('\n') if p.strip()][:8]
                    except Exception:
                        pass

                action["found_paths"] = paths
                if paths:
                    action["top_path"] = paths[0]
                    # Automatically reveal top match in Finder
                    if action.get("reveal", True):
                        try:
                            subprocess.Popen(["open", "-R", paths[0]])
                        except Exception:
                            pass
                    result = {
                        "executed": True,
                        "detail": f"Located {len(paths)} item(s) on Mac. Top match revealed in Finder: {paths[0]}"
                    }
                else:
                    result = {
                        "executed": False,
                        "detail": f"No files or items matching '{filename}' found on this Mac, Sir."
                    }

    except Exception as e:
        result = {"executed": False, "detail": f"macOS execution note: {e}"}

    action["result"] = result
    return result


# ─────────────────────────────────────────────────────────────────
# LOCAL GEMMA 2 MODEL INTEGRATION (Apple Silicon M2 / Ollama)
# ─────────────────────────────────────────────────────────────────
LOCAL_OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_GEMMA_MODEL = "gemma2:2b"


def call_local_gemma(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Call locally running Google Gemma 2 on Apple Silicon M2 via Ollama.
    High speed, private, offline.
    """
    global ai_success_count

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": m.get("content", "")})

    payload = {
        "model": LOCAL_GEMMA_MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 300,
        }
    }

    with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=15.0, write=2.0, pool=2.0)) as client:
        resp = client.post(LOCAL_OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data.get("message", {}).get("content", "")
        result = extract_json(raw_text)
        if isinstance(result, dict) and "action" in result and isinstance(result["action"], dict):
            act = result["action"]
            if act.get("command") == "CALCULATE" and "result" in act and not act.get("answer"):
                act["answer"] = str(act["result"])
        ai_success_count += 1
        return result



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
            "maxOutputTokens": 400,
            "candidateCount": 1,
        }
    }

    last_error = None
    for model in GOOGLE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=3.0, read=5.0, write=2.0, pool=2.0)) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

                # Guard: handle empty / blocked candidates gracefully
                candidates = data.get("candidates") or []
                if not candidates:
                    finish = data.get("promptFeedback", {}).get("blockReason", "EMPTY_RESPONSE")
                    raise ValueError(f"Gemini returned no candidates: {finish}")

                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                if not parts:
                    raise ValueError("Gemini candidate has no content parts")

                raw_text = parts[0].get("text", "")
                if not raw_text.strip():
                    raise ValueError("Gemini returned empty text")

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
            continue  # Try next model

    raise RuntimeError(f"All Google AI models failed. Last error: {last_error}")


# ─────────────────────────────────────────────────────────────────
# RESPONSE VALIDATION
# ─────────────────────────────────────────────────────────────────
def validate_response(data: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Ensure response schema is always correct and safe before returning to frontend."""
    # Ensure reply field exists and is a string
    if not isinstance(data.get("reply"), str) or not data["reply"].strip():
        data["reply"] = "Holographic array synchronized, Sir."

    # If raw JSON string leaked into reply, parse out the inner reply
    if data["reply"].strip().startswith("{"):
        reply_match = re.search(r'"reply"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', data["reply"])
        if reply_match:
            data["reply"] = reply_match.group(1).encode().decode('unicode_escape', errors='ignore')
        else:
            data["reply"] = "Action processed, Sir."

    # Truncate overly long replies
    if len(data["reply"]) > 300:
        data["reply"] = data["reply"][:297] + "..."

    # Ensure action is a dict
    if not isinstance(data.get("action"), dict):
        data["action"] = {"command": "NONE"}

    # Validate command
    cmd = str(data["action"].get("command", "NONE")).upper()
    if cmd not in VALID_COMMANDS:
        data["action"]["command"] = "NONE"
    else:
        data["action"]["command"] = cmd

    # If model returned NONE but the user query had an unambiguous command,
    # adopt deterministic fallback action while keeping model's spoken reply
    if data["action"]["command"] == "NONE":
        fb = fallback_jarvis_engine(user_text)
        if fb.get("action", {}).get("command") and fb["action"]["command"] != "NONE":
            data["action"] = fb["action"]

    # Command-specific field sanitization
    if data["action"]["command"] == "DEPLOY_WIDGET":
        if not isinstance(data["action"].get("widget_name"), str) or not data["action"]["widget_name"].strip():
            data["action"]["widget_name"] = PRESET_WIDGET_NAMES[len(chat_history) % len(PRESET_WIDGET_NAMES)]
    elif data["action"]["command"] == "SET_VOLUME":
        try:
            data["action"]["volume"] = max(0, min(100, int(data["action"].get("volume", 50))))
        except (ValueError, TypeError):
            data["action"]["volume"] = 50
    elif data["action"]["command"] == "OPEN_APP":
        if not data["action"].get("app_name"):
            data["action"]["app_name"] = "System Settings"
    elif data["action"]["command"] == "SEND_WHATSAPP":
        if not data["action"].get("message"):
            data["action"]["message"] = user_text
    elif data["action"]["command"] == "SEND_EMAIL":
        if not data["action"].get("to"):
            data["action"]["to"] = "contact@stark.com"
        if not data["action"].get("subject"):
            data["action"]["subject"] = "Update from J.A.R.V.I.S."
        if not data["action"].get("body"):
            data["action"]["body"] = user_text
    elif data["action"]["command"] == "CALCULATE":
        if not data["action"].get("app_name"):
            data["action"]["app_name"] = "Calculator"
        # If the model provided an expression or result, ensure answer is set
        if not data["action"].get("answer"):
            if data["action"].get("result") and isinstance(data["action"]["result"], (int, float, str)):
                data["action"]["answer"] = str(data["action"]["result"])
            elif data["action"].get("expression"):
                try:
                    expr = re.sub(r'[^0-9\+\-\*\/\%\.\(\)\s]', '', str(data["action"]["expression"]))
                    ans = eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}})
                    data["action"]["answer"] = str(int(ans) if isinstance(ans, float) and ans.is_integer() else round(ans, 6))
                except Exception:
                    pass
    elif data["action"]["command"] == "FIND_FILE":
        if not data["action"].get("filename"):
            data["action"]["filename"] = user_text

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
        return FileResponse(
            index_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="index.html not found.")


@app.post("/chat")
def chat_endpoint(payload: ChatInput):
    """
    POST /chat
    Accepts user text, routes through priority AI pipeline:
    1. Local Gemma 2 via Ollama (Apple Silicon M2)
    2. Google Gemini Flash (Cloud API)
    3. Resilient Fallback Engine
    Executes native macOS system automation & messaging, and returns J.A.R.V.I.S. response.
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

    response_data: Optional[Dict[str, Any]] = None
    engine_used = "J.A.R.V.I.S. Local Matrix (Fallback)"

    # 1. Attempt Local Gemma 2 via Ollama (Apple Silicon M2)
    try:
        response_data = call_local_gemma(chat_history)
        engine_used = "Local Gemma 2 (Apple M2)"
    except Exception as e:
        # print(f"[JARVIS] Local Gemma 2 unavailable: {e}")
        pass

    # 2. Attempt Google Gemini Flash (Cloud API)
    if not response_data:
        api_key = (os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
        if api_key and (api_key.startswith("AQ.") or api_key.startswith("AIza")):
            try:
                response_data = call_google_ai_studio(chat_history, api_key)
                engine_used = "Google Gemini Flash (Cloud)"
            except Exception as e:
                print(f"[JARVIS] Cloud AI failed: {e}")

    # 3. Rule-based offline engine
    if not response_data:
        response_data = fallback_jarvis_engine(user_text)
        engine_used = "J.A.R.V.I.S. Rule Engine (Offline)"

    # Validate and sanitize response
    response_data = validate_response(response_data, user_text)

    # Execute native macOS task (open app, adjust volume, launch WhatsApp / Gmail compose)
    execute_mac_task(response_data["action"])

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
        "engine": engine_used,
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
    Returns system health, local Gemma status, and session stats for the HUD.
    """
    api_key = (os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
    
    # Check if local Ollama Gemma is running
    local_gemma_online = False
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                local_gemma_online = any("gemma" in m for m in models)
    except Exception:
        local_gemma_online = False

    active_model = "gemma2:2b (Local Apple M2)" if local_gemma_online else ("gemini-flash-latest" if api_key else "local-fallback-engine")

    return {
        "status": "ONLINE",
        "version": "2.1.0",
        "ai_model": active_model,
        "local_gemma_online": local_gemma_online,
        "cloud_ai_connected": bool(api_key),
        "ai_connected": local_gemma_online or bool(api_key),
        "session_uptime_seconds": round(time.time() - session_start, 1),
        "history_length": len(chat_history),
        "request_count": request_count,
        "ai_success_count": ai_success_count,
        "fallback_count": fallback_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────
# LOCAL FASTER-WHISPER SPEECH TRANSCRIPTION ENDPOINT
# ─────────────────────────────────────────────────────────────────
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[JARVIS WHISPER INIT ERROR] {e}")
            _whisper_model = False
    return _whisper_model


def _sync_transcribe(content: bytes) -> str:
    model = get_whisper_model()
    if not model:
        return ""
    audio_stream = io.BytesIO(content)
    segments, _ = model.transcribe(
        audio_stream,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True,
    )
    return " ".join([s.text.strip() for s in segments if s.text]).strip()


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Local Whisper transcription endpoint.
    Transcribes audio recorded from frontend MediaRecorder (WebM, WAV, MP4, OGG).
    Runs completely offline on Apple Silicon / CPU in <150ms with zero cloud dependencies.
    """
    try:
        content = await audio.read()
        if not content or len(content) < 100:
            return {"text": "", "status": "empty"}

        transcribed_text = await asyncio.to_thread(_sync_transcribe, content)
        return {"text": transcribed_text, "status": "ok"}
    except Exception as e:
        print(f"[JARVIS WHISPER ERROR] {e}")
        return {"text": "", "error": str(e)}


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
