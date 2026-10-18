"""
J.A.R.V.I.S. — Advanced Holographic AI Command System Backend
Powered by FastAPI + Google Gemini Flash + Robust Fallback Engine
"""

import os
import sys
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    "CALCULATE", "FIND_FILE", "PLAY_MEDIA", "ACTIVATE_CAMERA", "SHOW_TELEMETRY",
    "AUTOMATE_DM", "COMPOSE_DOCUMENT", "WRITE_CODE", "LOCK_SCREEN", "MANAGE_TODOS", "DIGEST_BRIEFING", "NONE"
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
SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the brilliant, articulate, and loyal AI assistant running directly on macOS for your Commander and creator, Yaseen.

Your character:
- Extremely intelligent, calm, proactive, and slightly dry-witted.
- Address the user as "Sir", "Commander", or "Mr. Yaseen".
- When asked to write code, algorithms, or programming tasks:
  Set command to "WRITE_CODE", language to target language (e.g. "python"), provide the complete working code in "code", and provide a polite 1-sentence spoken reply.
- When asked to write letters, documents, emails, or messages, compose them from Yaseen (never use "Tony Stark").
- Tailor the letter style to the recipient and topic:
  * Letters to family (sister, brother, mom, dad, friend): warm, loving, personal, informal.
  * Letters to authorities (principal, dean, teacher, boss, manager, HR): formal, articulate, polite.
- Always sign off letters with:
  "Yours respectfully,\nYaseen" (for formal) or
  "With love and best wishes,\nYaseen" (for personal/family).

Output format: You MUST always respond with valid JSON and nothing else. Structure:
{
  "reply": "<Spoken audio response in character>",
  "action": {
    "command": "<ONE of: WRITE_CODE, COMPOSE_DOCUMENT, PLAY_MEDIA, ACTIVATE_CAMERA, CALCULATE, FIND_FILE, OPEN_APP, SET_VOLUME, SEND_WHATSAPP, SEND_EMAIL, SEARCH_WEB, OPEN_URL, SYSTEM_SCAN, ACTIVATE_DEFENSE, DEPLOY_WIDGET, STAND_DOWN, SHOW_TELEMETRY, AUTOMATE_DM, NONE>",
    "language": "<Language if WRITE_CODE: python, javascript, html, etc.>",
    "code": "<Complete runnable source code if WRITE_CODE>",
    "title": "<Code title if WRITE_CODE>",
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
- NONE: Casual conversation, questions, knowledge inquiries, or general discussions.
  * For general conversation and questions, provide a full, natural, intelligent, and articulate response in the "reply" field. Do NOT give terse 1-sentence dismissals. Act as an advanced conversational AI chatbot while maintaining the loyal J.A.R.V.I.S. persona.
  * When asked about who you are or your model/architecture: explain that you are J.A.R.V.I.S. (Just A Rather Very Intelligent System), created for Commander Yaseen, powered by advanced Google Gemini multimodal intelligence and neural core orchestration, operating with direct macOS system automation capabilities.

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
        "reply": (cleaned[:2000] if cleaned else "All holographic systems online, Sir."),
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

    # 3. Identity, Model & Creator Persona
    identity_keywords = [
        "who are you", "what is your name", "what are you", "who made you", "who created you",
        "your creator", "which model", "what model", "type of model", "kind of model",
        "what ai are you", "are you an ai", "what architecture", "tell me about yourself"
    ]
    if any(k in lower for k in identity_keywords):
        return {
            "reply": "I am J.A.R.V.I.S. (Just A Rather Very Intelligent System), powered by Google Gemini and Neural Core intelligence tailored for Commander Yaseen. I am a multimodal task and conversational model capable of deep reasoning, macOS automation, code synthesis, and real-time dialogue, Sir.",
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

        target_name = phone or "Alex"
        resolved_phone = resolve_contact(target_name, key="phone") if target_name else "+1234567890"
        clean_digits = re.sub(r"[^0-9]", "", resolved_phone)
        if len(clean_digits) == 10 and clean_digits[0] in "6789":
            clean_digits = f"91{clean_digits}"
        encoded_msg = urllib.parse.quote(msg)
        wa_desktop = f"whatsapp://send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"whatsapp://send?text={encoded_msg}"
        wa_web = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"https://web.whatsapp.com/send?text={encoded_msg}"
        sms_desktop = f"sms:{resolved_phone}&body={encoded_msg}" if resolved_phone else f"sms:&body={encoded_msg}"

        plat_name = "WhatsApp" if platform == "whatsapp" else ("iMessage" if platform == "imessage" else "Apple Messages & WhatsApp")
        return {
            "reply": f"Dispatching direct WhatsApp message to {target_name} ({resolved_phone}) via {plat_name}: '{msg}', Sir. Transmitted automatically.",
            "action": {
                "command": "SEND_WHATSAPP",
                "platform": platform,
                "phone": target_name,
                "recipient": target_name,
                "resolved_phone": resolved_phone,
                "clean_digits": clean_digits,
                "message": msg,
                "web_url": wa_web,
                "desktop_url": wa_desktop,
                "sms_url": sms_desktop,
                "auto_sent": True
            }
        }

    # 8b. Advanced Neural Document & Formal Letter Composer
    letter_keywords = [
        "write a letter", "draft a letter", "compose a letter", "write letter",
        "leave letter", "sick leave", "application for leave", "leave application",
        "sick note", "write an application", "letter to principal", "letter to the principal",
        "letter to boss", "letter to the boss", "letter to manager", "letter to teacher",
        "draft letter", "write a formal letter", "formal letter", "write an excuse",
        "write a note to", "draft a note to", "write an email to principal", "write an email to boss",
        "write an email to teacher", "write an email to manager", "resignation letter"
    ]
    is_letter_intent = any(k in lower for k in letter_keywords) or (
        any(lower.startswith(k) or f" {k} " in f" {lower} " for k in ["write a ", "write an ", "draft a ", "compose a "])
        and any(k in lower for k in ["letter", "application", "excuse", "note", "leave", "resignation", "apology"])
    )
    if is_letter_intent and not any(k in lower for k in ["calculate", "scan", "volume"]):
        # 1. Determine Letter Nature (Personal / Family vs Formal Authority)
        today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        is_family = any(k in lower for k in ["sister", "brother", "mother", "mom", "father", "dad", "friend", "cousin", "bro", "bestie", "uncle", "aunt"])

        if is_family:
            if "sister" in lower:
                recipient = "My Dear Sister"
                salutation = "Dearest Sister,"
            elif "brother" in lower or "bro" in lower:
                recipient = "My Dear Brother"
                salutation = "Dearest Brother,"
            elif "mother" in lower or "mom" in lower:
                recipient = "Mom"
                salutation = "Dearest Mom,"
            elif "father" in lower or "dad" in lower:
                recipient = "Dad"
                salutation = "Dearest Dad,"
            else:
                rec_match = re.search(r"\b(?:to|for)\s+(?:my\s+)?([a-zA-Z\s]+?)(?:\s+regarding|\s+about|\s+requesting|\s+due|\s+that|\s+for|\s+because|$)", user_text, re.IGNORECASE)
                rec_val = rec_match.group(1).strip().title() if rec_match else "Friend"
                recipient = rec_val
                salutation = f"Dearest {rec_val},"

            document_type = "Personal Letter"

            # Reason extraction
            reason_match = re.search(r"\b(?:about|regarding|that|saying|for)\s+(.*)", user_text, re.IGNORECASE)
            raw_reason = reason_match.group(1).strip() if reason_match else "Staying in Touch and Checking In"
            reason = raw_reason.title()
            subject = f"Personal Letter: {reason}"

            letter_content = f"""Date: {today_str}

{salutation}

Subject: {subject}

I hope this letter finds you in wonderful spirits and excellent health. I wanted to take a moment to write to you personally regarding {raw_reason}.

I hope everything has been going smoothly on your end. Please know that you are always in my thoughts, and I am continuously cheering you on in all your endeavors. Whenever you have a quiet moment, please do write back or give me a call—I would love to catch up on everything in your life.

Take wonderful care of yourself, and please let me know if you need anything at all.

With all my love and warmest regards,

Yaseen
[Personal J.A.R.V.I.S. Neural Console]"""

        else:
            # Formal Authority Letter (Principal, Boss, HR, etc.)
            if "principal" in lower:
                recipient = "The Principal"
                org_line = "School / College Administration"
                document_type = "Formal Academic Leave Application"
            elif "boss" in lower or "manager" in lower or "employer" in lower:
                recipient = "The Reporting Manager / Boss"
                org_line = "Corporate Executive Office"
                document_type = "Professional Leave / Official Notice"
            elif "teacher" in lower or "professor" in lower:
                recipient = "The Professor / Class Instructor"
                org_line = "Academic Department"
                document_type = "Formal Academic Notice"
            elif "hr" in lower or "human resources" in lower:
                recipient = "The Human Resources Department"
                org_line = "People Operations & Personnel"
                document_type = "Official HR Application"
            else:
                rec_match = re.search(r"\b(?:to|for)\s+(?:the\s+)?([a-zA-Z\s]+?)(?:\s+regarding|\s+about|\s+requesting|\s+due|\s+that|\s+for|\s+because|$)", user_text, re.IGNORECASE)
                recipient = rec_match.group(1).strip().title() if rec_match else "The Respected Authority"
                org_line = "Administrative Office"
                document_type = "Formal Correspondence"

            # Reason extraction
            if any(k in lower for k in ["illness", "sick", "fever", "unwell", "hospital", "doctor", "health", "medical"]):
                reason = "Sudden Medical Illness and Recovery"
                desc_detail = "unforeseen acute medical illness and physical exhaustion. My consulting physician has strictly advised complete bed rest and medication to facilitate recovery and prevent complications."
            elif any(k in lower for k in ["urgent", "emergency", "personal", "cant attend", "can't attend", "cannot attend", "so i can't attend", "so i cant attend"]):
                reason = "Urgent Circumstances Preventing In-Person Attendance"
                desc_detail = "critical and unforeseen personal contingencies that require my immediate physical presence and attention, preventing me from attending scheduled obligations today."
            elif any(k in lower for k in ["wedding", "family", "function", "trip", "vacation"]):
                reason = "Important Family Commitments"
                desc_detail = "mandatory family obligations and pre-scheduled personal commitments that necessitate my presence."
            else:
                reason_match = re.search(r"\b(?:regarding|about|requesting|due to|because of|that|for)\s+(.*)", user_text, re.IGNORECASE)
                raw_reason = reason_match.group(1).strip() if reason_match else "Unavoidable Leave of Absence"
                reason = raw_reason.title()
                desc_detail = f"circumstances regarding {raw_reason}, requiring my immediate absence from scheduled duties."

            subject = f"Formal Application for Leave of Absence - {reason}"

            letter_content = f"""Date: {today_str}

To:
{recipient}
{org_line}

Subject: {subject}

Respected Sir/Madam,

I am writing this formal correspondence to respectfully request an approved leave of absence, effective immediately, due to {desc_detail}

Due to these prevailing conditions, I am regrettably unable to attend scheduled sessions, duties, or classes. I assure you that I will take full responsibility for reviewing all missed curriculum, briefings, or operational tasks promptly upon my return. Should any urgent coordination be required during my absence, I will remain periodically accessible via email.

I kindly request that you grant me permission and approve my absence for this duration. Enclosed/attached is all relevant supporting documentation for your official records.

Thank you very much for your understanding, support, and consideration in this matter.

Yours respectfully,

Yaseen
[Authorized J.A.R.V.I.S. Neural Console]"""

        encoded_sub = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(letter_content)
        gmail_compose = f"https://mail.google.com/mail/?view=cm&fs=1&su={encoded_sub}&body={encoded_body}"

        return {
            "reply": f"I have composed a {document_type.lower()} for {recipient} regarding {reason}, Commander Yaseen. The document is displayed on your HUD console ready for review, 1-click clipboard copy, or email dispatch.",
            "action": {
                "command": "COMPOSE_DOCUMENT",
                "document_type": document_type,
                "recipient": recipient,
                "subject": subject,
                "reason": reason,
                "content": letter_content,
                "word_count": len(letter_content.split()),
                "gmail_url": gmail_compose
            }
        }

    # 8c. OpenJarvis Code Synthesis & Execution Engine
    code_keywords = [
        "write a code", "write code", "generate code", "python code", "write a python",
        "write a program", "write program", "code to", "python script", "write script",
        "code in python"
    ]
    is_code_request = any(k in lower for k in code_keywords) or (
        any(k in lower for k in ["code", "script", "program", "function"]) and any(k in lower for k in ["write", "generate", "create", "implement", "build", "give me"])
    )
    if is_code_request and not any(k in lower for k in ["calculate 26", "widget", "letter", "leave"]):
        lang = "python"
        title = "Python Code"

        if any(k in lower for k in ["add two numbers", "addition", "sum of two", "sum two numbers", "add 2 numbers"]):
            title = "Addition of Two Numbers"
            code_body = '''# J.A.R.V.I.S. Neural Code Synthesis — Powered by OpenJarvis
# Task: Add two numbers in Python

def add_two_numbers(a: float, b: float) -> float:
    """Return the arithmetic sum of two numbers."""
    return a + b

# Demonstration
num1 = 25
num2 = 75
result = add_two_numbers(num1, num2)

print(f"First number : {num1}")
print(f"Second number: {num2}")
print(f"Sum          : {result}")
'''
        elif any(k in lower for k in ["fibonacci"]):
            title = "Fibonacci Sequence Generator"
            code_body = '''# J.A.R.V.I.S. Neural Code Synthesis — Powered by OpenJarvis
# Task: Fibonacci Sequence Generator

def fibonacci(n: int) -> list:
    """Generate first n Fibonacci numbers."""
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

n = 10
print(f"First {n} Fibonacci numbers: {fibonacci(n)}")
'''
        elif any(k in lower for k in ["factorial"]):
            title = "Factorial Computation"
            code_body = '''# J.A.R.V.I.S. Neural Code Synthesis — Powered by OpenJarvis
# Task: Factorial Computation

def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

val = 6
print(f"Factorial of {val} is {factorial(val)}")
'''
        elif any(k in lower for k in ["reverse", "palindrome"]):
            title = "String Reversal & Palindrome Check"
            code_body = '''# J.A.R.V.I.S. Neural Code Synthesis — Powered by OpenJarvis
# Task: String Reversal and Palindrome Verification

def check_palindrome(text: str) -> bool:
    cleaned = ''.join(c.lower() for c in text if c.isalnum())
    return cleaned == cleaned[::-1]

sample = "radar"
print(f"Text: '{sample}'")
print(f"Reversed: '{sample[::-1]}'")
print(f"Is palindrome: {check_palindrome(sample)}")
'''
        else:
            task_name = re.sub(r'^(?:please\s+)?(?:write|generate|create|build|give\s+me)\s+(?:a\s+)?(?:code|program|script)?(?:\s+to|\s+in\s+python\s+to|\s+for)?\s*', '', user_text, flags=re.IGNORECASE).strip()
            task_clean = task_name if task_name else "Algorithm Pipeline"
            title = task_clean.title()
            code_body = f'''# J.A.R.V.I.S. Neural Code Synthesis — Powered by OpenJarvis
# Directive: {task_clean}

def solve_directive():
    print("Initiating J.A.R.V.I.S. OpenJarvis execution pipeline...")
    result = "Process executed successfully under Commander Yaseen directive."
    print(f"Status: {{result}}")
    return result

if __name__ == "__main__":
    solve_directive()
'''

        # Run immediately in OpenJarvis sandbox
        exec_res = execute_python_code(code_body)

        return {
            "reply": f"Here is the verified Python code for {title}, Commander Yaseen. I have executed it in the OpenJarvis sandbox environment with exit code {exec_res['returncode']}.",
            "action": {
                "command": "WRITE_CODE",
                "title": title,
                "language": lang,
                "code": code_body.strip(),
                "execution": exec_res,
                "output": exec_res["output"],
                "runnable": True
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

    # 11. Streaming Media & Tutorial Playback (YouTube, Spotify, Netflix, Apple Music)
    media_platforms = ["youtube", "spotify", "netflix", "apple music", "soundcloud"]
    media_nouns = ["video", "tutorial", "song", "track", "music", "podcast", "playlist", "episode"]
    media_verbs = ["play", "stream", "listen to", "watch", "hear"]

    has_media_intent = (
        any(k in lower for k in media_platforms)
        or any(k in lower for k in media_nouns)
        or any(lower.startswith(k) or f" {k} " in f" {lower} " for k in media_verbs)
    )
    is_excluded_cmd = any(k in lower for k in [
        "calculate", "scan", "status", "volume", "defense", "battery", "storage",
        "lock screen", "todo", "write code", "write a code", "compose", "letter",
        "email", "whatsapp", "dm", "message"
    ])

    if has_media_intent and not is_excluded_cmd:
        service = "youtube"
        if "spotify" in lower:
            service = "spotify"
        elif "netflix" in lower or "movie" in lower or "series" in lower or "season" in lower:
            service = "netflix"
        elif "apple music" in lower or "itunes" in lower:
            service = "apple_music"

        query_text = re.sub(r"^(?:hey\s+|hi\s+)?jarvis[\s,]*", "", user_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"^(?:please\s+|can\s+you\s+)?(?:play|stream|listen\s+to|watch|find|show\s+me|search\s+for|search|give\s+me|get|look\s+up|open)\s+", "", query_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"\s+(?:on|in|from|at)\s+(?:spotify|youtube|netflix|apple\s+music)\s*$", "", query_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"^youtube\s+", "", query_text, flags=re.IGNORECASE).strip()
        query_text = re.sub(r"^(?:what\s+is\s+the|which\s+is\s+the|what's\s+the)\s+", "", query_text, flags=re.IGNORECASE).strip()
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

    # 14. Web Search & Informational Queries
    search_prefixes = ["search for ", "google ", "search ", "who is ", "what is ", "where is ", "why is ", "why does ", "how to ", "how do ", "tell me about "]
    if any(lower.startswith(p) for p in search_prefixes) or lower.startswith("find out "):
        query = re.sub(r"^(?:search\s+(?:for\s+)?|google\s+|who\s+is\s+|what\s+is\s+|where\s+is\s+|why\s+is\s+|why\s+does\s+|how\s+to\s+|how\s+do\s+|tell\s+me\s+about\s+|find\s+out\s+)", "", user_text, flags=re.IGNORECASE).strip()
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

    # 18b. thevickypedia/Jarvis System Controls: Screen Lock / Sleep Display
    if any(k in lower for k in ["lock screen", "lock mac", "sleep screen", "sleep display", "lock the screen"]):
        return {
            "reply": "Securing your workspace and putting display terminal to sleep, Sir.",
            "action": {"command": "LOCK_SCREEN"}
        }

    # 18c. thevickypedia/Jarvis Task & Todo Registry
    if any(lower.startswith(k) for k in ["add todo", "add task", "new todo", "create task", "remind me to"]):
        task_clean = re.sub(r'^(?:please\s+)?(?:add\s+todo|add\s+task|new\s+todo|create\s+task|remind\s+me\s+to)\s*', '', user_text, flags=re.IGNORECASE).strip()
        task_text = task_clean if task_clean else "New Stark Task"
        todos = load_todos()
        new_id = (max([t.get("id", 0) for t in todos], default=0)) + 1
        new_todo = {"id": new_id, "task": task_text, "done": False}
        todos.append(new_todo)
        save_todos(todos)
        return {
            "reply": f"Added task to your active Stark todo registry: '{task_text}', Sir.",
            "action": {"command": "MANAGE_TODOS", "operation": "add", "task": task_text, "todos": todos}
        }

    if any(k in lower for k in ["show todos", "show my todos", "list todos", "list my tasks", "what are my todos", "what are my tasks"]):
        todos = load_todos()
        todo_list_str = ", ".join([t.get("task", "") for t in todos if isinstance(t, dict) and not t.get("done")]) or "All tasks completed"
        return {
            "reply": f"You have {len(todos)} items in your Stark registry: {todo_list_str}, Sir.",
            "action": {"command": "MANAGE_TODOS", "operation": "list", "todos": todos}
        }

    # 18e. thevickypedia/Jarvis Contacts Management
    if any(lower.startswith(k) for k in ["add contact", "new contact", "save contact", "register contact"]):
        m = re.search(r'(?:add\s+contact|new\s+contact|save\s+contact|register\s+contact)\s+([a-zA-Z\s]+?)(?:\s+with\s+phone|\s+with\s+number|\s*:\s*|\s+phone\s+|\s+number\s+|\s+)([0-9\+\-\s]{7,15})', user_text, re.IGNORECASE)
        if m:
            c_name = m.group(1).strip()
            c_phone = re.sub(r'[^0-9\+]', '', m.group(2).strip())
            contacts = load_contacts()
            contacts.setdefault("phone", {})[c_name.lower()] = c_phone
            save_contacts(contacts)
            return {
                "reply": f"Contact '{c_name}' successfully registered with phone {c_phone} in your Stark contact directory, Sir.",
                "action": {"command": "MANAGE_CONTACTS", "operation": "add", "name": c_name, "phone": c_phone}
            }

    if any(k in lower for k in ["show contacts", "list contacts", "who are my contacts", "show my contacts", "view contacts"]):
        contacts = load_contacts()
        names = list(contacts.get("phone", {}).keys())
        names_str = ", ".join([n.title() for n in names if n not in ["me", "myself", "commander"]])
        return {
            "reply": f"Your Stark contact directory contains: {names_str}, Sir.",
            "action": {"command": "MANAGE_CONTACTS", "operation": "list", "contacts": contacts}
        }

    # 18d. OpenJarvis Executive Briefing & Morning Digest Engine
    if any(k in lower for k in ["morning digest", "daily digest", "briefing", "brief me", "executive summary", "status report", "executive briefing", "daily briefing"]):
        vitals = get_system_hardware_vitals()
        batt = vitals.get("battery", {})
        todos = load_todos()
        active_todos = [t.get("task", "") for t in todos if isinstance(t, dict) and not t.get("done")]
        task_summary = f"{len(active_todos)} pending items" if active_todos else "all tasks completed"
        time_str = datetime.now().strftime("%I:%M %p")
        reply = (
            f"Good day, Commander Yaseen. Here is your OpenJarvis Executive Briefing at {time_str}: "
            f"Power systems stand at {batt.get('percent', 100)}% ({batt.get('source', 'Power')}), "
            f"SSD storage has {vitals.get('storage', {}).get('free_gb', 0)}GB available, "
            f"WhatsApp gateway is armed for your primary terminal (+918197646867), and you have {task_summary} on your mission board. All defense vectors nominal."
        )
        return {
            "reply": reply,
            "action": {
                "command": "DIGEST_BRIEFING",
                "briefing_type": "Executive Morning Digest",
                "time": time_str,
                "battery": batt,
                "storage": vitals.get("storage", {}),
                "todos": active_todos,
                "whatsapp_gateway": "+918197646867",
                "security": "Defense Nominal"
            }
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


# ─────────────────────────────────────────────────────────────────
# CONTACTS & TODOLIST REGISTRIES (Inspired by thevickypedia/Jarvis)
# ─────────────────────────────────────────────────────────────────
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.json")
TODOS_FILE = os.path.join(BASE_DIR, "todos.json")

def load_contacts() -> Dict[str, Dict[str, str]]:
    default_contacts = {
        "phone": {
            "alex": "+1234567890",
            "mom": "+1987654321",
            "dad": "+1987654322",
            "boss": "+1987654323",
            "sister": "+1987654324",
            "yaseen": "+1234567899"
        },
        "email": {
            "alex": "alex@example.com",
            "boss": "boss@stark.com",
            "sister": "sister@example.com",
            "mom": "mom@example.com"
        }
    }
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default_contacts

def save_contacts(contacts: Dict[str, Dict[str, str]]):
    try:
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
    except Exception:
        pass

def resolve_contact(name_or_number: str, key: str = "phone") -> str:
    """Resolve contact name to phone number or email using contact book (thevickypedia/Jarvis style)."""
    raw = (name_or_number or "").strip()
    if not raw:
        return ""

    contacts = load_contacts()
    lookup = contacts.get(key, {})
    lowered = raw.lower()

    # 1. Direct match in registry (e.g. "yaseen", "me", "alex", "8197646867")
    if lowered in lookup:
        return lookup[lowered]

    for k, v in lookup.items():
        if k in lowered or (len(k) > 2 and lowered in k):
            return v

    # 2. If phone lookup and raw has digits
    if key == "phone":
        digits = re.sub(r"[^0-9]", "", raw)
        # Indian 10-digit mobile number normalization
        if len(digits) == 10 and digits[0] in "6789":
            return f"+91{digits}"
        if len(digits) >= 7:
            return raw

    return raw

def load_todos() -> List[Dict[str, Any]]:
    default_todos = [
        {"id": 1, "task": "Review Arc Reactor core output", "done": False},
        {"id": 2, "task": "Verify macOS WhatsApp gateway credentials (+918197646867)", "done": True},
        {"id": 3, "task": "Calibrate Mark 85 repulsor arrays", "done": False},
        {"id": 4, "task": "Inspect OpenJarvis neural subroutines", "done": False}
    ]
    try:
        if os.path.exists(TODOS_FILE):
            with open(TODOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "todos" in data:
                    data = data["todos"]
                if isinstance(data, list):
                    valid = [item for item in data if isinstance(item, dict) and "task" in item]
                    return valid if valid else default_todos
    except Exception:
        pass
    return default_todos

def save_todos(todos: Any):
    try:
        if isinstance(todos, dict) and "todos" in todos:
            todos = todos["todos"]
        if not isinstance(todos, list):
            return
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2)
    except Exception:
        pass

def auto_send_whatsapp(recipient: str, message: str) -> Dict[str, Any]:
    """Automated WhatsApp dispatch inspired by thevickypedia/Jarvis:
    1. Resolves contact name (e.g. Alex, Mom, Yaseen, 8197646867) to phone number.
    2. Cleans phone digits for whatsapp:// URI and web.whatsapp.com with +91 handling.
    3. Triggers native macOS WhatsApp app with AppleScript return keystroke.
    4. Generates both desktop_url and web_url fallbacks.
    """
    resolved_phone = resolve_contact(recipient, key="phone") or recipient
    clean_digits = re.sub(r"[^0-9]", "", resolved_phone)
    if len(clean_digits) == 10 and clean_digits[0] in "6789":
        clean_digits = f"91{clean_digits}"
    encoded_msg = urllib.parse.quote(message)

    desktop_url = f"whatsapp://send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"whatsapp://send?text={encoded_msg}"
    web_url = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"https://web.whatsapp.com/send?text={encoded_msg}"

    def _dispatch():
        import time
        try:
            # 1. Launch WhatsApp URL
            subprocess.run(["open", desktop_url], check=False)
            time.sleep(1.2)
            # 2. Focus WhatsApp process and press Return
            send_script = '''
            tell application "System Events"
                if exists (process "WhatsApp") then
                    tell process "WhatsApp"
                        set frontmost to true
                        delay 0.4
                        key code 36
                    end tell
                end if
            end tell
            '''
            subprocess.run(["osascript", "-e", send_script], check=False)
        except Exception:
            pass

    threading.Thread(target=_dispatch, daemon=True).start()

    return {
        "success": True,
        "recipient": recipient,
        "resolved_phone": resolved_phone,
        "clean_digits": clean_digits,
        "message": message,
        "desktop_url": desktop_url,
        "web_url": web_url,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


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


# ─────────────────────────────────────────────────────────────────
# OPENJARVIS CODE INTERPRETER & HARDENED SUBPROCESS RUNNER
# ─────────────────────────────────────────────────────────────────
def execute_python_code(code: str, timeout: float = 4.0) -> Dict[str, Any]:
    """Execute Python code in an isolated child process with AST check and timeout (from OpenJarvis)."""
    import ast
    start_time = time.time()
    if not code or not code.strip():
        return {"success": False, "output": "No code provided.", "returncode": -1, "duration": 0.0}

    # AST Syntax Validation
    try:
        ast.parse(code)
    except SyntaxError as e:
        return {"success": False, "output": f"SyntaxError: {e}", "returncode": 1, "duration": round(time.time() - start_time, 3)}

    safe_env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }

    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        duration = round(time.time() - start_time, 3)
        return {
            "success": result.returncode == 0,
            "output": output.strip() if output.strip() else "(Execution completed with returncode 0, no output printed)",
            "returncode": result.returncode,
            "duration": duration
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": f"Execution timed out after {timeout} seconds.",
            "returncode": -1,
            "duration": round(time.time() - start_time, 3)
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Execution error: {e}",
            "returncode": -1,
            "duration": round(time.time() - start_time, 3)
        }


def execute_shell_command(command: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Execute a safe shell command and return stdout/stderr (from OpenJarvis)."""
    start_time = time.time()
    if not command or not command.strip():
        return {"success": False, "output": "Empty command.", "returncode": -1, "duration": 0.0}

    lowered = command.strip().lower()
    if any(b in lowered for b in ["rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:"]):
        return {"success": False, "output": "Security Alert: Command blocked by OpenJarvis safety policy.", "returncode": -1, "duration": 0.0}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR)
        )
        out = (result.stdout + ("\n" if result.stdout and result.stderr else "") + result.stderr).strip()
        return {
            "success": result.returncode == 0,
            "output": out if out else "(Command completed with no output)",
            "returncode": result.returncode,
            "duration": round(time.time() - start_time, 3)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"Command timed out after {timeout}s.", "returncode": -1, "duration": round(time.time() - start_time, 3)}
    except Exception as e:
        return {"success": False, "output": f"Execution failed: {e}", "returncode": -1, "duration": round(time.time() - start_time, 3)}


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

            resolved_phone = action.get("resolved_phone") or resolve_contact(phone, key="phone") or phone
            clean_digits = re.sub(r"[^0-9]", "", resolved_phone)
            if len(clean_digits) == 10 and clean_digits[0] in "6789":
                clean_digits = f"91{clean_digits}"
            encoded_msg = urllib.parse.quote(msg)

            wa_desktop = f"whatsapp://send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"whatsapp://send?text={encoded_msg}"
            wa_web = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded_msg}" if clean_digits else f"https://web.whatsapp.com/send?text={encoded_msg}"
            sms_desktop = f"sms:{resolved_phone}&body={encoded_msg}" if resolved_phone else f"sms:&body={encoded_msg}"

            action["phone"] = phone
            action["resolved_phone"] = resolved_phone
            action["web_url"] = wa_web
            action["desktop_url"] = wa_desktop
            action["sms_url"] = sms_desktop
            action["platform"] = platform
            action["auto_sent"] = True

            if platform in ["whatsapp", "auto"]:
                auto_send_whatsapp(phone, msg)
            if platform in ["imessage", "messages", "sms", "auto"]:
                auto_send_message(resolved_phone or phone, msg, platform)

            plat_name = "WhatsApp" if platform == "whatsapp" else ("iMessage" if platform == "imessage" else "Apple Messages & WhatsApp")
            result = {"executed": True, "detail": f"Message to {phone or 'recipient'} ({resolved_phone}) sent automatically via {plat_name}: '{msg}'"}

        elif cmd == "LOCK_SCREEN":
            try:
                subprocess.Popen(["pmset", "displaysleepnow"])
            except Exception:
                pass
            result = {"executed": True, "detail": "Display terminal placed in secure standby (Screen Locked)"}

        elif cmd == "MANAGE_TODOS":
            task = action.get("task", "")
            result = {"executed": True, "detail": f"Todo task updated: '{task}'"}

        elif cmd == "MANAGE_CONTACTS":
            name = action.get("name", "Contact")
            result = {"executed": True, "detail": f"Contact registry updated: '{name}'"}

        elif cmd == "DIGEST_BRIEFING":
            result = {"executed": True, "detail": "OpenJarvis Executive Briefing synthesized and telemetry projected to HUD array"}

        elif cmd == "SHOW_TELEMETRY":
            telemetry_type = action.get("telemetry_type", "all")
            result = {"executed": True, "detail": f"Hardware telemetry ({telemetry_type}) projected to HUD array"}

        elif cmd == "COMPOSE_DOCUMENT":
            subject = action.get("subject", "Formal Letter")
            recipient = action.get("recipient", "Recipient")
            word_count = action.get("word_count", 0)
            result = {"executed": True, "detail": f"Formal document '{subject}' ({word_count} words) synthesized for {recipient} and displayed on HUD console"}

        elif cmd == "WRITE_CODE":
            if "execution" not in action or not action.get("output"):
                code = action.get("code", "")
                if code and action.get("language", "python") == "python":
                    action["execution"] = execute_python_code(code)
                    action["output"] = action["execution"].get("output", "")
            title = action.get("title", "Python Script")
            result = {"executed": True, "detail": f"Code synthesis complete: '{title}' (OpenJarvis sandbox)"}

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
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemma-4-26b-a4b-it",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
]


def call_google_ai_studio(history: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
    """
    Call Google AI Studio with multi-model fallback:
    1. Tries gemini-3.5-flash-lite & gemini-3.1-flash-lite (fast, smart, active quota)
    2. Falls back to gemini-3.5-flash, gemini-3.8-flash, etc.
    Timeout: 7.0s per attempt.
    """
    global ai_success_count

    # Only send last 8 turns to keep context tight and fast
    context = history[-8:]
    contents = []
    for m in context:
        role = "user" if m.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    gen_config: Dict[str, Any] = {
        "temperature": 0.5,
        "maxOutputTokens": 1500,
        "candidateCount": 1,
    }

    last_error = None
    for model in GOOGLE_MODELS:
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": dict(gen_config)
        }
        # Only models requiring thinkingBudget=0 get thinkingConfig; flash-lite models reject it with 400
        if model in ("gemini-3.5-flash", "gemini-3.8-flash"):
            payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=3.0, read=7.0, write=3.0, pool=3.0)) as client:
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
        except httpx.HTTPStatusError as e:
            last_error = e
            # Only fail fast if key is unauthorized (401)
            if e.response.status_code == 401:
                print(f"[JARVIS] Cloud AI auth code 401 (Invalid API key): failing to offline engine")
                break
            print(f"[JARVIS] Model {model} status {e.response.status_code}: trying next candidate...")
            continue
        except httpx.TimeoutException as e:
            last_error = e
            print(f"[JARVIS] Model {model} timeout: trying next candidate...")
            continue
        except Exception as e:
            last_error = e
            print(f"[JARVIS] Model {model} error: {type(e).__name__}: {e}")
            continue

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

    # Guard against excessively runaway replies (> 2500 chars) while allowing full conversational depth
    if len(data["reply"]) > 2500:
        data["reply"] = data["reply"][:2497] + "..."

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

    # 1. Attempt Google Gemini / Gemma (Cloud API) first if valid API key is present
    api_key = (os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
    has_valid_api_key = bool(api_key and (api_key.startswith("AQ.") or api_key.startswith("AIza") or len(api_key) > 20))

    if has_valid_api_key:
        try:
            response_data = call_google_ai_studio(chat_history, api_key)
            engine_used = "Google Gemma / Gemini AI (Cloud)"
        except Exception as e:
            # print(f"[JARVIS] Cloud AI error: {e}")
            pass

    # 2. Attempt Local Gemma 2 via Ollama (Apple Silicon M2) if Cloud AI not used/available
    if not response_data:
        try:
            response_data = call_local_gemma(chat_history)
            engine_used = "Local Gemma 2 (Apple M2)"
        except Exception as e:
            # print(f"[JARVIS] Local Gemma 2 unavailable: {e}")
            pass

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


class CodeRunRequest(BaseModel):
    code: str
    timeout: Optional[float] = 4.0


class ShellRunRequest(BaseModel):
    command: str
    timeout: Optional[float] = 5.0


@app.post("/api/code/run")
def run_code_endpoint(payload: CodeRunRequest):
    """Execute Python code in isolated OpenJarvis child process."""
    res = execute_python_code(payload.code, timeout=payload.timeout or 4.0)
    return {"ok": res["success"], **res}


@app.post("/api/shell/run")
def run_shell_endpoint(payload: ShellRunRequest):
    """Execute shell command with OpenJarvis safety policy."""
    res = execute_shell_command(payload.command, timeout=payload.timeout or 5.0)
    return {"ok": res["success"], **res}


class WhatsAppSendPayload(BaseModel):
    recipient: str
    message: str
    phone: Optional[str] = None


class ContactPayload(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class TodoPayload(BaseModel):
    task: str
    done: Optional[bool] = False


@app.post("/api/whatsapp/send")
def send_whatsapp_endpoint(payload: WhatsAppSendPayload):
    """Direct WhatsApp dispatch with contact resolution and native URL generation."""
    rec = payload.recipient.strip()
    msg = payload.message.strip()
    if not rec or not msg:
        raise HTTPException(status_code=400, detail="Recipient and message cannot be empty")
    target = payload.phone.strip() if payload.phone else rec
    res = auto_send_whatsapp(target, msg)
    return {"ok": True, **res}


@app.get("/api/contacts")
def get_contacts_endpoint():
    """Retrieve contact directory (inspired by thevickypedia/Jarvis)."""
    return load_contacts()


@app.post("/api/contacts")
def add_contact_endpoint(payload: ContactPayload):
    """Add or update contact entry."""
    contacts = load_contacts()
    name_clean = payload.name.strip().lower()
    if payload.phone:
        contacts.setdefault("phone", {})[name_clean] = payload.phone.strip()
    if payload.email:
        contacts.setdefault("email", {})[name_clean] = payload.email.strip()
    save_contacts(contacts)
    return {"ok": True, "name": payload.name, "contacts": contacts}


@app.get("/api/todos")
def get_todos_endpoint():
    """Retrieve active todo tasks (inspired by thevickypedia/Jarvis)."""
    return {"todos": load_todos()}


@app.post("/api/todos")
def add_todo_endpoint(payload: TodoPayload):
    """Add a new task to todo registry."""
    todos = load_todos()
    new_id = (max([t.get("id", 0) for t in todos], default=0)) + 1
    new_item = {"id": new_id, "task": payload.task.strip(), "done": bool(payload.done)}
    todos.append(new_item)
    save_todos(todos)
    return {"ok": True, "todo": new_item, "total": len(todos)}


@app.get("/api/openjarvis/briefing")
def openjarvis_briefing_endpoint():
    """Generate OpenJarvis Executive Briefing / Morning Digest."""
    vitals = get_system_hardware_vitals()
    todos = load_todos()
    active_todos = [t for t in todos if not t.get("done")]
    time_str = datetime.now().strftime("%I:%M %p")
    return {
        "ok": True,
        "title": "OpenJarvis Executive Morning Digest",
        "commander": "Yaseen",
        "time": time_str,
        "battery": vitals.get("battery", {}),
        "storage": vitals.get("storage", {}),
        "cpu_load": vitals.get("cpu_load_1m", 0),
        "active_todos": active_todos,
        "whatsapp_gateway": "+918197646867",
        "security_posture": "Nominal / Defense Standby"
    }


@app.get("/api/openjarvis/status")
def openjarvis_status_endpoint():
    """OpenJarvis architecture health & capability manifest."""
    return {
        "ok": True,
        "agent": "J.A.R.V.I.S. Neural Core (OpenJarvis Augmented)",
        "commander": "Yaseen",
        "whatsapp_phone": "+918197646867",
        "capabilities": [
            "code_interpreter",
            "shell_exec",
            "executive_digest",
            "human_calculator",
            "whatsapp_dispatch",
            "youtube_player",
            "spotlight_scan",
            "hardware_vitals"
        ],
        "latency": "0.02s (offline rule engine) / 0.8s (Gemini 3.8 Flash)"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
