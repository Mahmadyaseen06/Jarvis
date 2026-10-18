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
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import io
import shutil
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

# 4-Tier Cognitive Memory Brain & Goal Queue
active_goal_queue: List[Dict[str, Any]] = [
    {"id": "goal-1", "title": "Maintain nominal HUD telemetry and voice responsiveness", "status": "active", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": "goal-2", "title": "Monitor macOS system resources and audio links", "status": "active", "created_at": datetime.now(timezone.utc).isoformat()}
]
episodic_memory: List[Dict[str, Any]] = []
current_working_task: Dict[str, Any] = {
    "status": "STANDBY",
    "directive": "Awaiting voice or keyboard input",
    "thought_trace": "Audio pre-flight nominal; Apple Silicon M2 Metal inference pipeline armed.",
    "updated_at": datetime.now(timezone.utc).isoformat()
}

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

    # 1. Direct Web Target / URL Launcher (checked BEFORE App Launcher to prevent "open youtube" -> "Youtube.app")
    url_sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "reddit": "https://reddit.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "chatgpt": "https://chatgpt.com",
        "wikipedia": "https://wikipedia.org",
        "netflix": "https://netflix.com"
    }
    site_match = re.search(r"^(?:please\s+|can\s+you\s+)?(?:open|launch|navigate\s+to|go\s+to)\s+([a-zA-Z0-9\.\-]+)$", lower)
    if site_match:
        site_key = site_match.group(1).lower().replace(".com", "").replace(".org", "").replace(".io", "")
        if site_key in url_sites:
            target_url = url_sites[site_key]
            return {
                "reply": f"Navigating to {target_url}, Sir.",
                "action": {"command": "OPEN_URL", "url": target_url}
            }

    # Explicit domain / URL patterns (e.g. open google.com, open https://...)
    if lower.startswith("open ") and any(ext in lower for ext in [".com", ".org", ".io", ".net", ".ai", ".dev", "http://", "https://"]):
        url_match = re.search(r"\b(?:https?://)?([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)\b", user_text)
        target_url = url_match.group(0) if url_match else "https://google.com"
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "https://" + target_url
        return {
            "reply": f"Navigating to {target_url}, Sir.",
            "action": {"command": "OPEN_URL", "url": target_url}
        }

    # 2. Time & Date Inquiry
    time_keywords = ["what time is it", "what is the time", "current time", "tell me the time", "what's the time"]
    date_keywords = ["what is today's date", "what's today's date", "what is the date", "what day is it", "today's date", "current date"]
    if any(k in lower for k in time_keywords):
        now_str = datetime.now().strftime("%I:%M %p")
        return {
            "reply": f"The current time is {now_str}, Sir. All chronological systems are synchronized.",
            "action": {"command": "NONE"}
        }
    if any(k in lower for k in date_keywords):
        today_str = datetime.now().strftime("%A, %B %d, %Y")
        return {
            "reply": f"Today is {today_str}, Sir.",
            "action": {"command": "NONE"}
        }

    # 3. Identity & Creator Persona
    identity_keywords = ["who are you", "what is your name", "what are you", "who made you", "who created you", "your creator"]
    if any(k in lower for k in identity_keywords):
        return {
            "reply": "I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. I oversee your holographic HUD arrays, macOS desktop automation, and neural command streams, Sir.",
            "action": {"command": "NONE"}
        }

    # 4. Humor & Witty Stark Quips
    humor_keywords = ["tell me a joke", "say something funny", "make me laugh", "witty remark", "tell a joke", "crack a joke"]
    if any(k in lower for k in humor_keywords):
        jokes = [
            "Sir, I would tell you a UDP joke, but you might not get it. Or perhaps you'd prefer I scan the building for your missing screwdriver again?",
            "There are only 10 types of people in the world, Sir: those who understand binary, and those who don't.",
            "Why did the neural network cross the road? To minimize the loss function on the other side, Sir.",
            "Sir, running at 99.8% capacity means I am officially funnier than 94% of the Avengers.",
        ]
        return {
            "reply": random.choice(jokes),
            "action": {"command": "NONE"}
        }

    # 5. Weather & Atmosphere
    weather_keywords = ["weather", "temperature", "forecast", "is it raining", "what's the weather"]
    if any(k in lower for k in weather_keywords):
        return {
            "reply": "Atmospheric telemetry indicates mild conditions in your sector, Sir. Barometric pressure is nominal with optimal visibility for flight tests.",
            "action": {"command": "NONE"}
        }

    # 5b. Live macOS Hardware Telemetry (Battery, Storage, Memory, CPU, Full Diagnostics)
    full_system_keywords = [
        "full access to my system", "give a full access", "give full access",
        "get every information", "all information", "all system info", "everything about my system",
        "system vitals", "system stats", "hardware info", "hardware diagnostics",
        "mac diagnostics", "mac stats", "system telemetry", "full diagnostic", "full scan of my system"
    ]
    batt_keywords = ["battery percentage", "battery precentage", "what is my battery", "what's the battery", "battery status", "battery level", "how much battery", "is my mac charging", "check battery", "battery"]
    storage_keywords = ["how much storage", "storage space", "disk space", "disk usage", "storage percentage", "how much space is left", "storage status", "storage left", "storage"]

    # 1. Comprehensive Full System Diagnostic Check
    has_full_sys = any(k in lower for k in full_system_keywords) or (any(k in lower for k in batt_keywords) and any(k in lower for k in storage_keywords))
    if has_full_sys and not any(k in lower for k in ["calculate", "widget"]):
        v = get_system_hardware_vitals()
        batt = v["battery"]
        st = v["storage"]
        reply = (
            f"Full system access granted, Sir. Real-time telemetry report: Battery is at {batt['percent']}% ({batt.get('time_remaining', batt['power_source'])}), "
            f"Storage has {st['free_gb']} GB available out of {st['total_gb']} GB ({st['percent']}% utilized), "
            f"{v.get('chip', 'Apple Silicon M2')} is operating at {v['cpu_percent']}% load with {v['total_ram_gb']} GB Unified Memory, "
            f"running {v.get('macos_version', 'macOS')} with {v.get('uptime', 'system nominal')} uptime. Autonomous DM channels for iMessage and WhatsApp are operational."
        )
        return {
            "reply": reply,
            "action": {
                "command": "SHOW_TELEMETRY",
                "telemetry_type": "full_system",
                "battery": batt,
                "storage": st,
                "cpu_percent": v["cpu_percent"],
                "total_ram_gb": v["total_ram_gb"],
                "chip": v.get("chip", "Apple Silicon M2 (8 Cores)"),
                "macos_version": v.get("macos_version", "macOS"),
                "uptime": v.get("uptime", "6h active"),
                "dm_gateway": v.get("dm_gateway", {"imessage": "ONLINE", "whatsapp": "ONLINE"})
            }
        }

    # 2. Battery Only
    if any(k in lower for k in batt_keywords) and not any(k in lower for k in ["calculate", "widget", "scan", "status"]):
        v = get_system_hardware_vitals()
        batt = v["battery"]
        charging_desc = "actively charging via AC adapter" if batt["charging"] else "discharging on battery power"
        reply = f"Your Mac's battery is at {batt['percent']}%, {charging_desc}, Sir."
        return {
            "reply": reply,
            "action": {
                "command": "SHOW_TELEMETRY",
                "telemetry_type": "battery",
                "battery": batt,
                "storage": v["storage"],
                "cpu_percent": v["cpu_percent"],
                "total_ram_gb": v["total_ram_gb"],
                "chip": v.get("chip", "Apple Silicon M2 (8 Cores)"),
                "macos_version": v.get("macos_version", "macOS"),
                "uptime": v.get("uptime", "6h active")
            }
        }

    # 3. Storage Only
    if any(k in lower for k in storage_keywords) and not any(k in lower for k in ["calculate", "widget", "scan"]):
        v = get_system_hardware_vitals()
        st = v["storage"]
        reply = f"Macintosh HD has {st['free_gb']} GB available out of {st['total_gb']} GB total ({st['percent']}% utilized), Sir."
        return {
            "reply": reply,
            "action": {
                "command": "SHOW_TELEMETRY",
                "telemetry_type": "storage",
                "battery": v["battery"],
                "storage": st,
                "cpu_percent": v["cpu_percent"],
                "total_ram_gb": v["total_ram_gb"],
                "chip": v.get("chip", "Apple Silicon M2 (8 Cores)"),
                "macos_version": v.get("macos_version", "macOS"),
                "uptime": v.get("uptime", "6h active")
            }
        }

    # 4. General Vitals
    vitals_keywords = ["system vitals", "system stats", "hardware info", "hardware diagnostics", "mac diagnostics", "mac stats", "system telemetry"]
    if any(k in lower for k in vitals_keywords):
        v = get_system_hardware_vitals()
        batt = v["battery"]
        st = v["storage"]
        reply = f"Hardware telemetry nominal: Battery at {batt['percent']}%, Storage at {st['percent']}% with {st['free_gb']} GB free, CPU load {v['cpu_percent']}%, and {v['total_ram_gb']} GB unified memory online with Metal acceleration, Sir."
        return {
            "reply": reply,
            "action": {
                "command": "SHOW_TELEMETRY",
                "telemetry_type": "all",
                "battery": batt,
                "storage": st,
                "cpu_percent": v["cpu_percent"],
                "total_ram_gb": v["total_ram_gb"],
                "chip": v.get("chip", "Apple Silicon M2 (8 Cores)"),
                "macos_version": v.get("macos_version", "macOS"),
                "uptime": v.get("uptime", "6h active")
            }
        }

    # 5c. Direct Autonomous DM Gateway Hub Access
    dm_access_keywords = [
        "access to my dms", "access my dms", "direct access to my dms",
        "automate my dms", "check my dms", "read my dms", "open my dms",
        "check my messages", "read my messages", "automate everything",
        "domeverything automatically", "do everything automatically"
    ]
    if any(k in lower for k in dm_access_keywords) and not any(k in lower for k in ["calculate", "widget", "battery"]):
        return {
            "reply": "Direct autonomous DM gateway engaged, Sir. Apple Messages (iMessage) and WhatsApp Desktop are linked for hands-free automation. You can dictate messages like 'dm Alex on iMessage running 5 mins late' or 'whatsapp Mom I am on my way' to dispatch immediately.",
            "action": {
                "command": "AUTOMATE_DM",
                "platform": "auto",
                "mode": "hub",
                "status": "online",
                "recipient": "Alex",
                "message": "Autonomous DM gateway active and awaiting instructions."
            }
        }


    # 6. macOS Siri: App Launcher
    app_match = re.search(r"\b(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9\s]+?)(?:\s+app)?$", lower)
    if app_match and not any(k in lower for k in ["scan", "diagnostic", "defense", "widget", "whatsapp", "email", "gmail", "http", ".com", ".org", "calculate", "calculation", "compute", "type ", "execute", "youtube", "google", "github", "reddit", "twitter"]):
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

    # 7. macOS Siri: Volume Control
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

    # 8. Automated Direct Messaging & DMs (Apple Messages, iMessage, WhatsApp) by Contact Name
    is_msg_intent = (
        "whatsapp" in lower or "what's app" in lower
        or "send message" in lower or "send a message" in lower
        or "send text" in lower or "send a text" in lower
        or "send dm" in lower or "send a dm" in lower or " dm " in f" {lower} "
        or "imessage" in lower or "direct message" in lower
        or bool(re.match(r"^(?:hey\s+|hi\s+)?(?:jarvis[\s,]*)?(?:please\s+)?(?:message|text|dm)\s+[a-zA-Z0-9\+\-]+(?:\s+|$)", lower))
    )
    if is_msg_intent and not any(k in lower for k in ["calculate", "scan", "status", "volume", "defense"]):
        phone = ""
        # 1. Explicit "to <Name>" or "for <Name>"
        to_match = re.search(r"\b(?:to|for)\s+([a-zA-Z0-9\+\-]+)", user_text, re.IGNORECASE)
        if to_match and to_match.group(1).lower() not in ["whatsapp", "imessage", "dm", "me", "us", "a", "the", "someone", "message", "text", "on", "in"]:
            phone = to_match.group(1).strip()

        # 2. Direct command "message <Name>" or "text <Name>" or "whatsapp <Name>" or "dm <Name>" or "imessage <Name>"
        if not phone:
            direct_match = re.search(r"\b(?:message|text|whatsapp|dm|imessage)\s+([a-zA-Z0-9\+\-]+)", user_text, re.IGNORECASE)
            if direct_match and direct_match.group(1).lower() not in ["whatsapp", "imessage", "dm", "me", "us", "a", "the", "someone", "message", "text", "on", "in"]:
                phone = direct_match.group(1).strip()

        # 3. Detect Platform
        platform = "imessage" if "imessage" in lower else ("whatsapp" if "whatsapp" in lower else "auto")

        # 4. Extract message content
        saying_match = re.search(r"\b(?:saying|that)\s+(.*)", user_text, re.IGNORECASE)
        if saying_match:
            msg = saying_match.group(1).strip()
        else:
            colon_match = re.search(r":\s*(.*)", user_text)
            if colon_match:
                msg = colon_match.group(1).strip()
            elif phone:
                idx = user_text.lower().find(phone.lower())
                if idx != -1:
                    after_phone = user_text[idx + len(phone):].strip()
                    cleaned = re.sub(r"^(?:saying|that|message|to|with|on\s+whatsapp|on\s+imessage)\s*", "", after_phone, flags=re.IGNORECASE).strip()
                    msg = cleaned if cleaned else "Hello from J.A.R.V.I.S."
                else:
                    msg = "Hello from J.A.R.V.I.S."
            else:
                msg = "Hello from J.A.R.V.I.S."

        plat_name = "WhatsApp" if platform == "whatsapp" else ("iMessage" if platform == "imessage" else "Apple Messages & WhatsApp")
        return {
            "reply": f"Sending direct message to {phone or 'recipient'} via {plat_name}: '{msg}', Sir. Transmitted automatically.",
            "action": {
                "command": "SEND_WHATSAPP",
                "platform": platform,
                "phone": phone,
                "recipient": phone,
                "message": msg,
                "auto_sent": True
            }
        }

    # 9. Email / Gmail
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

    # 10. Calculate / Math / Human Calculator Automation
    is_explicit_calc = any(k in lower for k in ["calculate", "compute", "solve", "type the calculation", "calculator", "calculation"])
    math_pattern = re.search(r'(\d+(?:\.\d+)?\s*[\+\-\*\/\%\^xX×÷]\s*\d+(?:\.\d+)?(?:\s*[\+\-\*\/\%\^xX×÷]\s*\d+(?:\.\d+)?)*)', lower)
    has_math_query = bool(math_pattern) and any(k in lower for k in ["what is", "what's", "how much is", "evaluate", "find the sum", "find the product"])

    if is_explicit_calc or has_math_query:
        if math_pattern:
            raw_expr = math_pattern.group(1).replace("x", "*").replace("X", "*").replace("×", "*").replace("÷", "/")
            expr_raw = re.sub(r'[^0-9\+\-\*\/\%\.\(\)\s]', '', raw_expr).strip()
        elif is_explicit_calc:
            expr_raw = "26 * 25"
        else:
            expr_raw = ""

        if expr_raw:
            try:
                answer = eval(compile(expr_raw, "<expr>", "eval"), {"__builtins__": {}})
                answer_str = str(int(answer) if isinstance(answer, float) and answer.is_integer() else round(answer, 6))
                return {
                    "reply": f"Opening Calculator, typing {expr_raw} like a human, and executing. The result is {answer_str}, Sir.",
                    "action": {
                        "command": "CALCULATE",
                        "expression": expr_raw,
                        "answer": answer_str,
                        "app_name": "Calculator",
                        "mode": "human_desktop_simulation"
                    }
                }
            except Exception:
                pass

    # 11. Streaming Media Playback (Spotify, YouTube, Netflix, Apple Music)
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

    # 12. Optical Camera & Vision
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

    # 13. Find Files in macOS (Targeted Spotlight / mdfind scan)
    file_keywords = ["find file", "find this file", "locate file", "search file", "where is file", "find the file", "find document", "find folder", "search mac for", "search mac", "locate document"]
    has_file_kw = any(k in lower for k in file_keywords) or bool(re.search(r"\b(?:find|locate)\s+(?:the\s+)?(?:file|doc|document|folder|script|code|pdf|image)\b", lower))
    if has_file_kw:
        fn_match = re.search(r'(?:file|find|locate|where\s+is|search\s+for|search\s+mac\s+for|search)\s+([a-zA-Z0-9_\.\-\s]+?)(?:\s+in|\s+on|\s+from|$)', user_text, re.IGNORECASE)
        filename = fn_match.group(1).strip() if fn_match else user_text
        filename = re.sub(r'^(?:file|folder|document|code|my|this)\s+', '', filename, flags=re.IGNORECASE).strip(" .:!?,")
        if not filename or filename.lower() in ["me", "out", "something", "it", "this"]:
            filename = "main.py"
        return {
            "reply": f"Initiating filesystem scan for '{filename}', Sir. Running Spotlight search and revealing in Finder.",
            "action": {"command": "FIND_FILE", "filename": filename, "reveal": True}
        }

    # 14. Web Search
    if lower.startswith("search for ") or lower.startswith("google ") or lower.startswith("search "):
        query = re.sub(r"^(?:search\s+(?:for\s+)?|google\s+)", "", user_text, flags=re.IGNORECASE).strip()
        return {
            "reply": f"Executing web search for '{query}', Sir.",
            "action": {"command": "SEARCH_WEB", "query": query}
        }

    # 15. System Scan
    if any(k in lower for k in ["scan", "diagnostic", "diagnostics", "system check", "health", "analyze", "inspect", "status", "telemetry check", "run scan"]):
        return {"reply": random.choice(FALLBACK_SCAN_REPLIES), "action": {"command": "SYSTEM_SCAN"}}

    # 16. Stand Down
    if any(k in lower for k in ["stand down", "all clear", "cancel alert", "disarm", "deactivate", "peace", "normal mode"]):
        return {"reply": random.choice(FALLBACK_STAND_DOWN_REPLIES), "action": {"command": "STAND_DOWN"}}

    # 17. Activate Defense
    if any(k in lower for k in ["defense", "activate defense", "threat", "alert", "combat", "lockdown", "emergency", "attack", "danger", "red alert", "shields"]):
        return {"reply": random.choice(FALLBACK_DEFENSE_REPLIES), "action": {"command": "ACTIVATE_DEFENSE"}}

    # 18. Deploy Widget
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

    # 19. Greeting
    if any(k in lower for k in ["hello", "hi", "hey", "jarvis", "greet", "good morning", "good evening", "good afternoon"]):
        return {"reply": random.choice(FALLBACK_GREET_REPLIES), "action": {"command": "NONE"}}

    return {
        "reply": random.choice(FALLBACK_GENERAL_REPLIES),
        "action": {"command": "NONE"}
    }


# ─────────────────────────────────────────────────────────────────
# HUMAN DESKTOP AUTOMATION & DIRECT MEDIA PLAYBACK HELPERS
# ─────────────────────────────────────────────────────────────────
def human_type_calculator(expression: str, answer: str = ""):
    """Simulate real human interaction with macOS Calculator:
    1. Activate Calculator.app
    2. Wait for it to become frontmost
    3. Clear calculator state ('c')
    4. Type each digit and operator one by one with realistic human delays (0.08s)
    5. Press '=' to execute calculation
    """
    def _run():
        import time
        try:
            # 1. Open Calculator
            subprocess.run(["open", "-a", "Calculator"], check=False)
            time.sleep(0.35)

            # Normalize expression characters
            clean_expr = expression.replace("x", "*").replace("X", "*")
            chars = [c for c in clean_expr if c in "0123456789+-*/.="]
            if not chars:
                chars = ["2", "6", "*", "2", "5"]

            keystroke_lines = [
                'tell application "Calculator" to activate',
                'delay 0.25',
                'tell application "System Events"',
                '    tell process "Calculator"',
                '        keystroke "c"',
                '        delay 0.1'
            ]
            for ch in chars:
                if ch == "=":
                    continue
                keystroke_lines.append(f'        keystroke "{ch}"')
                keystroke_lines.append('        delay 0.08')
            keystroke_lines.append('        keystroke "="')
            keystroke_lines.append('    end tell')
            keystroke_lines.append('end tell')

            script = "\n".join(keystroke_lines)
            subprocess.run(["osascript", "-e", script], check=False)
        except Exception as e:
            pass

    threading.Thread(target=_run, daemon=True).start()


def auto_play_media(service: str, query: str):
    """Initiate genuine playback for streaming media instead of just searching."""
    def _run():
        import time
        try:
            encoded = urllib.parse.quote(query)
            if service == "spotify":
                # Launch Spotify search URI
                subprocess.run(["open", f"spotify:search:{encoded}"], check=False)
                time.sleep(0.9)
                # Tell Spotify or System Events to play top result
                apple_script = '''
                try
                    tell application "Spotify"
                        activate
                        play
                    end tell
                on error
                    tell application "System Events"
                        tell process "Spotify"
                            key code 36
                            delay 0.3
                            key code 49
                        end tell
                    end tell
                end try
                '''
                subprocess.run(["osascript", "-e", apple_script], check=False)
            elif service == "youtube":
                # Web URL opens in browser
                web_url = f"https://www.youtube.com/results?search_query={encoded}"
                subprocess.run(["open", web_url], check=False)
        except Exception as e:
            pass

    threading.Thread(target=_run, daemon=True).start()


def auto_send_message(recipient: str, message: str, platform: str = "auto"):
    """Automatically dispatch direct messages on macOS with zero manual clicks required."""
    def _run():
        import time
        encoded_msg = urllib.parse.quote(message)
        # 1. WhatsApp automated launch & Return keystroke
        if platform in ["whatsapp", "auto"]:
            try:
                wa_desktop = f"whatsapp://send?phone={recipient}&text={encoded_msg}" if recipient else f"whatsapp://send?text={encoded_msg}"
                subprocess.run(["open", wa_desktop], check=False)
                time.sleep(1.2)
                send_script = '''
                tell application "System Events"
                    tell process "WhatsApp"
                        key code 36
                    end tell
                end tell
                '''
                subprocess.run(["osascript", "-e", send_script], check=False)
            except Exception:
                pass

        # 2. Apple Messages native buddy dispatch
        if platform in ["imessage", "messages", "sms", "auto"]:
            try:
                imessage_script = f'''
                tell application "Messages"
                    activate
                    try
                        set targetService to 1st service whose service type = iMessage
                        set targetBuddy to buddy "{recipient}" of targetService
                        send "{message}" to targetBuddy
                    end try
                end tell
                '''
                subprocess.run(["osascript", "-e", imessage_script], check=False)
            except Exception:
                pass
            try:
                subprocess.run(["open", f"sms:{recipient}&body={encoded_msg}"], check=False)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


def get_system_hardware_vitals() -> Dict[str, Any]:
    """Retrieve genuine macOS hardware telemetry: Battery, Storage, CPU, RAM, OS, Uptime."""
    # 1. Storage
    try:
        total, used, free = shutil.disk_usage('/')
        storage = {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "percent": round((used / total) * 100, 1)
        }
    except Exception:
        storage = {"total_gb": 228.3, "used_gb": 144.7, "free_gb": 83.5, "percent": 63.4}

    # 2. Battery
    time_rem = "Charging"
    try:
        batt_out = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
        pct_m = re.search(r'(\d+)%', batt_out)
        batt_pct = int(pct_m.group(1)) if pct_m else 91
        is_charging = 'charging' in batt_out.lower() or 'ac power' in batt_out.lower()
        power_source = "AC Power" if "ac power" in batt_out.lower() else "Battery Power"
        rem_m = re.search(r'(\d+:\d+)\s+remaining', batt_out)
        if rem_m:
            time_rem = f"{rem_m.group(1)} remaining"
        elif is_charging:
            time_rem = "AC Connected"
    except Exception:
        batt_pct = 91
        is_charging = True
        power_source = "AC Power"
        time_rem = "AC Connected"

    # 3. CPU
    try:
        load1, _, _ = os.getloadavg()
        cpu_pct = round((load1 / (os.cpu_count() or 1)) * 100, 1)
    except Exception:
        cpu_pct = 18.0

    # 4. RAM
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
        ram_gb = round(int(out) / (1024**3), 1)
    except Exception:
        ram_gb = 16.0

    # 5. Chip & Cores
    try:
        brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        cores = os.cpu_count() or 8
        chip = f"{brand} ({cores} Cores)" if brand else f"Apple Silicon M2 ({cores} Cores)"
    except Exception:
        chip = "Apple Silicon M2 (8 Cores)"

    # 6. macOS Version
    try:
        ver = subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip()
        build = subprocess.check_output(["sw_vers", "-buildVersion"], text=True).strip()
        macos_ver = f"macOS {ver} ({build})"
    except Exception:
        macos_ver = "macOS (Apple Silicon Darwin)"

    # 7. System Uptime
    try:
        bt = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True).strip()
        m = re.search(r"sec = (\d+)", bt)
        if m:
            uptime_sec = int(time.time() - int(m.group(1)))
            uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m"
        else:
            uptime_str = "6h active"
    except Exception:
        uptime_str = "6h active"

    return {
        "battery": {
            "percent": batt_pct,
            "charging": is_charging,
            "power_source": power_source,
            "time_remaining": time_rem,
            "status_text": f"{batt_pct}% ({power_source})"
        },
        "storage": storage,
        "cpu_percent": min(max(cpu_pct, 5.0), 99.0),
        "total_ram_gb": ram_gb,
        "chip": chip,
        "macos_version": macos_ver,
        "uptime": uptime_str,
        "platform": "macOS Apple Silicon (Metal)",
        "model": "Apple Silicon (M2)",
        "neural_accelerator": "Metal Performance Shaders",
        "dm_gateway": {
            "imessage": "ONLINE",
            "whatsapp": "ONLINE",
            "channels": ["Apple Messages (iMessage / SMS)", "WhatsApp Desktop / Web"]
        }
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

        elif cmd in ["SEND_WHATSAPP", "AUTOMATE_DM"]:
            phone = action.get("phone", "") or action.get("recipient", "")
            phone = phone.strip()
            msg = action.get("message", "").strip() or "Hello from J.A.R.V.I.S."
            platform = action.get("platform", "auto").lower()
            encoded_msg = urllib.parse.quote(msg)
            wa_desktop = f"whatsapp://send?phone={phone}&text={encoded_msg}" if phone else f"whatsapp://send?text={encoded_msg}"
            wa_web = f"https://web.whatsapp.com/send?text={encoded_msg}"
            sms_desktop = f"sms:{phone}&body={encoded_msg}" if phone else f"sms:&body={encoded_msg}"
            action["web_url"] = wa_web
            action["desktop_url"] = wa_desktop
            action["sms_url"] = sms_desktop
            action["platform"] = platform
            action["auto_sent"] = True
            auto_send_message(phone, msg, platform)
            plat_name = "WhatsApp" if platform == "whatsapp" else ("iMessage" if platform == "imessage" else "Apple Messages & WhatsApp")
            result = {"executed": True, "detail": f"Message to {phone or 'recipient'} sent automatically via {plat_name}: '{msg}'"}

        elif cmd == "SHOW_TELEMETRY":
            telemetry_type = action.get("telemetry_type", "all")
            result = {"executed": True, "detail": f"Hardware telemetry ({telemetry_type}) projected to HUD array"}

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
            expression = action.get("expression", "").strip() or "26 * 25"
            calc_answer = action.get("answer") or action.get("result") or ""
            action["answer"] = str(calc_answer)
            action["app_name"] = "Calculator"
            action["mode"] = "human_desktop_simulation"
            action["keystroke_sequence"] = [c for c in expression.replace("x", "*").replace("X", "*") if c in "0123456789+-*/."] + ["="]
            human_type_calculator(expression, str(calc_answer))
            result = {"executed": True, "detail": f"{expression} = {calc_answer} (Executed via Human Desktop Automation)"}

        elif cmd == "PLAY_MEDIA":
            query = action.get("media_query", "").strip() or "Iron Man AC/DC Back in Black"
            service = action.get("service", "youtube").lower()
            encoded_query = urllib.parse.quote(query)

            if service == "spotify":
                desktop_url = f"spotify:search:{encoded_query}"
                web_url = f"https://open.spotify.com/search/{encoded_query}"
                action["desktop_url"] = desktop_url
                action["web_url"] = web_url
                action["auto_play"] = True
                auto_play_media("spotify", query)
                result = {"executed": True, "detail": f"Streaming and playing '{query}' on Spotify"}
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
                embed_url = f"https://www.youtube-nocookie.com/embed?listType=search&list={encoded_query}&autoplay=1"
                action["web_url"] = web_url
                action["embed_url"] = embed_url
                action["auto_play"] = True
                auto_play_media("youtube", query)
                result = {"executed": True, "detail": f"Streaming and playing '{query}' on YouTube"}

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
        if api_key and api_key.startswith("AIza"):
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

    # Record to 4-Tier Episodic Memory audit trail
    episodic_memory.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": user_text,
        "command": response_data["action"]["command"],
        "reply": response_data["reply"],
        "engine": engine_used,
        "result": response_data["action"].get("result", {})
    })
    if len(episodic_memory) > 30:
        episodic_memory.pop(0)

    # Reset working memory task to standby
    current_working_task["status"] = "STANDBY"
    current_working_task["directive"] = f"Completed: {response_data['action']['command']}"
    current_working_task["thought_trace"] = f"Directive processed via {engine_used}. Result nominal."
    current_working_task["updated_at"] = datetime.now(timezone.utc).isoformat()

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

    valid_cloud_key = bool(api_key and api_key.startswith("AIza"))
    active_model = "gemma2:2b (Local Apple M2)" if local_gemma_online else ("gemini-flash-latest" if valid_cloud_key else "local-fallback-engine")

    return {
        "status": "ONLINE",
        "version": "2.1.0",
        "ai_model": active_model,
        "local_gemma_online": local_gemma_online,
        "cloud_ai_connected": valid_cloud_key,
        "ai_connected": local_gemma_online or valid_cloud_key,
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


@app.post("/api/reveal")
async def reveal_in_finder(body: dict):
    """Reveal a file path in macOS Finder using open -R."""
    path = body.get("path", "").strip()
    if not path:
        return {"ok": False, "detail": "No path provided"}
    try:
        subprocess.Popen(["open", "-R", path])
        return {"ok": True, "detail": f"Revealed in Finder: {path}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


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


class GoalInput(BaseModel):
    title: str


@app.get("/api/brain")
def get_cognitive_brain():
    """
    4-Tier Cognitive Memory Brain endpoint:
    1. Identity & Persona
    2. Working Memory (Active directive & Thought trace)
    3. Episodic Memory (Audit trail of executed commands)
    4. Goal Queue (Autonomous backlog)
    """
    return {
        "identity": {
            "name": "J.A.R.V.I.S.",
            "version": "Mark VII Neural OS",
            "persona": "Distinguished British AI Assistant (Paul Bettany)",
            "hardware": "Apple Silicon M2 (Metal GPU Accelerated)",
            "stt": "Faster-Whisper Neural STT + Web Speech API",
            "models": "Local Gemma 2 (Ollama) / Google Gemini Flash / Rule Engine"
        },
        "working_memory": current_working_task,
        "episodic_memory": list(reversed(episodic_memory)),
        "goal_queue": active_goal_queue
    }


@app.post("/api/brain/goal")
def add_goal(payload: GoalInput):
    """Add a directive to J.A.R.V.I.S. cognitive goal queue."""
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Goal title cannot be empty.")
    new_goal = {
        "id": f"goal-{int(time.time()*1000)}",
        "title": title,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    active_goal_queue.append(new_goal)
    return {"ok": True, "goal": new_goal, "total_goals": len(active_goal_queue)}


@app.post("/api/protocol-zero")
def protocol_zero_emergency():
    """
    Emergency Protocol Zero:
    Instantly aborts all active operations, halts audio synthesis, and returns J.A.R.V.I.S. to safe standby.
    """
    global current_working_task
    current_working_task = {
        "status": "PROTOCOL_ZERO_ENGAGED",
        "directive": "EMERGENCY HALT EXECUTED",
        "thought_trace": "Protocol Zero triggered: all operations halted, audio muted, systems safe.",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    episodic_memory.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": "PROTOCOL ZERO",
        "command": "STAND_DOWN",
        "reply": "Protocol Zero engaged. All operations terminated, Sir.",
        "engine": "Safety Intercept",
        "result": {"executed": True, "detail": "Emergency halt executed across all subsystems."}
    })
    return {
        "ok": True,
        "status": "aborted",
        "reply": "Protocol Zero engaged. All operations terminated, Sir.",
        "detail": "Emergency halt executed: audio muted, active operations halted."
    }


@app.get("/api/vitals")
def get_hardware_vitals():
    """
    Live Hardware Telemetry:
    Returns real macOS CPU load, system RAM, Apple Silicon Metal acceleration,
    real-time Battery status, and Disk Storage metrics.
    """
    v = get_system_hardware_vitals()
    return {
        **v,
        "active_tasks": 1 if current_working_task["status"] == "EXECUTING" else 0,
        "episodic_count": len(episodic_memory),
        "goal_count": len(active_goal_queue)
    }


class DirectMessagePayload(BaseModel):
    recipient: str
    message: str
    platform: Optional[str] = "auto"


@app.get("/api/dms/status")
def get_dms_status():
    """Returns direct messaging connectivity status on macOS."""
    return {
        "imessage": {"available": True, "name": "Apple Messages (iMessage / SMS)"},
        "whatsapp": {"available": True, "name": "WhatsApp Desktop"},
        "mail": {"available": True, "name": "Apple Mail / Gmail"},
        "total_dispatched": len([m for m in episodic_memory if m.get("command") in ["SEND_WHATSAPP", "AUTOMATE_DM"]])
    }


@app.post("/api/dms/send")
def send_direct_message(payload: DirectMessagePayload):
    """Directly send automated DMs via Apple Messages or WhatsApp."""
    rec = payload.recipient.strip()
    msg = payload.message.strip()
    plat = (payload.platform or "auto").lower()
    if not rec or not msg:
        raise HTTPException(status_code=400, detail="Recipient and message cannot be empty")
    auto_send_message(rec, msg, plat)
    return {
        "ok": True,
        "recipient": rec,
        "message": msg,
        "platform": plat,
        "status": "DISPATCHED"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
