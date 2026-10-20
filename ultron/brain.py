"""
Ultron AI Reasoning Engine (brain.py)
Flexible, production-grade LLM client supporting 100% free-tier options:
1. Groq (Free high-speed cloud inference: llama-3.3-70b-versatile, llama3-8b-8192)
2. Google AI Studio (Free Gemini: gemini-2.5-flash, gemini-1.5-flash)
3. Local Ollama (100% Free, zero-API-key local offline inference: llama3.2, mistral, gemma2)
4. Offline Deterministic Fallback Engine (Runs even with zero network or missing keys)

Formats tool schemas into system instructions and returns structured JSON actions.
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

from tools import TOOL_CATALOG

logger = logging.getLogger("ultron.brain")

SYSTEM_INSTRUCTION = """You are Ultron, an elite, free open-source autonomous desktop automation agent.
Your mission is to understand natural language instructions from the user and generate safe, structured execution commands.

Available Tools:
{tool_specs}

Rules:
1. You MUST respond with ONLY a single valid JSON object. Do not include markdown preamble or commentary outside the JSON.
2. Structure your JSON response EXACTLY as follows:
{{
  "thought": "Your internal reasoning explaining what the user wants and which tool/params are appropriate.",
  "tool": "exact_tool_name_from_list",
  "params": {{ "param_name": "param_value" }},
  "reply": "Clear, professional user-facing reply describing the action being taken."
}}
3. If the user prompt is conversational (e.g., greetings, questions about who you are, jokes, or general queries not requiring desktop interaction), set "tool" to "none", "params" to {{}}, and provide your response in "reply".
4. For desktop paths: if no directory is specified, default to the user's Desktop.
5. Always double check that parameter names and types match the tool specifications.
"""


def _generate_tool_specs() -> str:
    """Formats the declarative TOOL_CATALOG into a concise text prompt for the LLM."""
    lines = []
    for tool in TOOL_CATALOG:
        params_desc = []
        for p_name, p_info in tool.get("parameters", {}).items():
            req = "required" if p_info.get("required") else "optional"
            params_desc.append(f"{p_name} ({p_info.get('type')}, {req}): {p_info.get('description')}")
        params_str = ", ".join(params_desc) if params_desc else "no parameters"
        lines.append(f"- {tool['name']}: {tool['description']}\n  Parameters: [{params_str}]")
    return "\n".join(lines)


class UltronBrain:
    """
    Reasoning client for Ultron desktop automation agent.
    Supports free cloud providers (Groq, Google AI Studio) and local Ollama.
    """

    def __init__(self, provider: Optional[str] = None):
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        pref = provider or os.getenv("DEFAULT_LLM_PROVIDER", "auto")
        self.provider, self.model_name = self._resolve_provider(pref)
        logger.info(f"Ultron Brain initialized with provider: {self.provider} ({self.model_name})")

    def _resolve_provider(self, preference: str) -> Tuple[str, str]:
        """Resolves the best available free-tier provider based on keys and preference."""
        pref = preference.lower().strip()
        
        # 1. Groq explicitly requested or available
        if pref in ("groq", "auto") and self.groq_key and not self.groq_key.startswith("gsk_your_"):
            return "groq", "llama-3.3-70b-versatile"
        
        # 2. Gemini explicitly requested or available
        if pref in ("gemini", "google") and self.gemini_key and not self.gemini_key.startswith("AIzaSy_your_"):
            return "gemini", "gemini-2.5-flash"
        
        # 3. Ollama explicitly requested or local fallback
        if pref in ("ollama", "local"):
            return "ollama", self.ollama_model
        
        # Auto cascade: Groq -> Gemini -> Ollama -> Offline Fallback
        if self.groq_key and not self.groq_key.startswith("gsk_your_"):
            return "groq", "llama-3.3-70b-versatile"
        if self.gemini_key and not self.gemini_key.startswith("AIzaSy_your_"):
            return "gemini", "gemini-2.5-flash"
        
        # Default to Ollama with offline rule engine safety
        return "ollama", self.ollama_model

    def get_system_prompt(self) -> str:
        """Builds the comprehensive system prompt."""
        return SYSTEM_INSTRUCTION.format(tool_specs=_generate_tool_specs())

    def think(self, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes natural language user prompt through the LLM engine and returns structured JSON command.
        
        Args:
            user_prompt: Natural language command from user.
            context: Optional contextual parameters (active window, current screen, etc.)
            
        Returns:
            Dict containing:
              - thought: str
              - tool: str
              - params: dict
              - reply: str
              - provider: str
        """
        prompt = user_prompt.strip()
        if not prompt:
            return {
                "thought": "Empty user input received.",
                "tool": "none",
                "params": {},
                "reply": "How can I assist you with your desktop automation today?",
                "provider": "builtin",
            }

        # Attempt primary resolved provider
        response_json = None
        used_provider = self.provider

        try:
            if self.provider == "groq":
                response_json = self._call_groq(prompt)
            elif self.provider == "gemini":
                response_json = self._call_gemini(prompt)
            elif self.provider == "ollama":
                response_json = self._call_ollama(prompt)
        except Exception as e:
            logger.warning(f"Primary provider '{self.provider}' failed ({e}). Checking fallback cascade...")
            
            # Cascade: try Gemini if Groq failed
            if self.provider != "gemini" and self.gemini_key and not self.gemini_key.startswith("AIzaSy_your_"):
                try:
                    response_json = self._call_gemini(prompt)
                    used_provider = "gemini"
                except Exception as ex:
                    logger.warning(f"Gemini fallback failed: {ex}")
            
            # Cascade: try Ollama if others failed
            if not response_json and self.provider != "ollama":
                try:
                    response_json = self._call_ollama(prompt)
                    used_provider = "ollama"
                except Exception as ex:
                    logger.warning(f"Ollama fallback failed: {ex}")

        # If LLM calls succeeded, parse structured JSON
        if response_json:
            parsed = self._clean_and_parse_json(response_json)
            if parsed:
                parsed["provider"] = used_provider
                return parsed

        # Ultimate safety: Offline Rule-Based Fallback Parser
        logger.info("Engaging offline deterministic rule engine for intent resolution.")
        offline_parsed = self._offline_fallback_parse(prompt)
        offline_parsed["provider"] = "offline_rule_engine"
        return offline_parsed

    def _call_groq(self, user_prompt: str) -> str:
        """Calls Groq Cloud API using standard HTTP (compatible with or without groq package)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
            "User-Agent": "Ultron-Desktop-Agent/1.0",
        }
        payload = {
            "model": self.model_name if "llama" in self.model_name else "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 800,
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _call_gemini(self, user_prompt: str) -> str:
        """Calls Google AI Studio Gemini API via REST."""
        # Models: gemini-2.5-flash or gemini-1.5-flash
        model = self.model_name if "gemini" in self.model_name else "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        
        system_text = self.get_system_prompt()
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_text}\n\nUser Command: {user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            }
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_ollama(self, user_prompt: str) -> str:
        """Calls local Ollama instance via HTTP API."""
        url = f"{self.ollama_host}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"]

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Cleans and extracts JSON payload from markdown fences or mixed output."""
        if not raw_text:
            return None
        
        cleaned = raw_text.strip()
        # Remove ```json and ``` fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        
        # Match outermost curly braces
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            candidate = match.group(0)
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    # Normalize keys
                    return {
                        "thought": str(data.get("thought", "Action parsed successfully.")),
                        "tool": str(data.get("tool", "none")),
                        "params": data.get("params", {}) if isinstance(data.get("params"), dict) else {},
                        "reply": str(data.get("reply", "Executing requested desktop action.")),
                    }
            except json.JSONDecodeError as err:
                logger.warning(f"JSON decode failed on candidate: {err}")
        
        return None

    def _offline_fallback_parse(self, user_prompt: str) -> Dict[str, Any]:
        """
        Deterministic, offline rule engine that reliably maps user intents
        to desktop actions when no external API or local LLM server is accessible.
        """
        low = user_prompt.lower().strip()

        # 1. Screenshot / Vision
        if any(w in low for w in ["screenshot", "screen capture", "capture screen", "snapshot", "take a picture"]):
            return {
                "thought": "User requested a desktop screen capture.",
                "tool": "vision.capture_screenshot",
                "params": {"prefix": "screen"},
                "reply": "Capturing full-screen screenshot now.",
            }

        # 2. Create Folder
        create_folder_match = re.search(r"(?:create|make|build)(?:\s+a)?\s+folder\s+(?:called|named)?\s*['\"]?([a-zA-Z0-9_\-\s]+)['\"]?", low)
        if create_folder_match:
            folder_name = create_folder_match.group(1).strip().strip("'\"")
            return {
                "thought": f"Detected request to create folder '{folder_name}'.",
                "tool": "file_manager.create_folder",
                "params": {"folder_name": folder_name},
                "reply": f"Creating directory '{folder_name}' on your Desktop.",
            }

        # 3. Create File
        create_file_match = re.search(r"(?:create|make|write)(?:\s+a)?\s+file\s+(?:called|named)?\s*['\"]?([a-zA-Z0-9_\-\.]+)['\"]?(?:\s+(?:with|content|containing)\s+['\"]?([\s\S]+?)['\"]?)?$", user_prompt, re.IGNORECASE)
        if create_file_match:
            file_name = create_file_match.group(1).strip().strip("'\"")
            content = create_file_match.group(2).strip().strip("'\"") if create_file_match.group(2) else ""
            return {
                "thought": f"Detected request to create file '{file_name}'.",
                "tool": "file_manager.create_file",
                "params": {"file_name": file_name, "content": content},
                "reply": f"Creating file '{file_name}' on your Desktop.",
            }

        # 4. List Directory / Files
        if any(w in low for w in ["list files", "show files", "show desktop", "list desktop", "what files", "view directory"]):
            return {
                "thought": "User requested directory listing of the desktop.",
                "tool": "file_manager.list_directory",
                "params": {},
                "reply": "Scanning and listing files on your Desktop.",
            }

        # 5. Delete File / Folder
        delete_match = re.search(r"(?:delete|remove|trash)\s+(?:the\s+)?(?:file|folder|item)?\s*['\"]?([a-zA-Z0-9_\-\.\s]+)['\"]?", low)
        if delete_match:
            target = delete_match.group(1).strip().strip("'\"")
            return {
                "thought": f"User requested defensive deletion of '{target}'.",
                "tool": "file_manager.delete_item",
                "params": {"target_path": target},
                "reply": f"Defensively removing '{target}' from the Desktop.",
            }

        # 6. Open Application
        open_app_match = re.search(r"(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+app|\s+application)?$", low)
        if open_app_match and not any(w in low for w in ["file", "folder"]):
            app_name = open_app_match.group(1).strip().title()
            return {
                "thought": f"User requested to launch application '{app_name}'.",
                "tool": "automation.open_application",
                "params": {"app_name": app_name},
                "reply": f"Launching application '{app_name}'.",
            }

        # 7. Type Text
        type_match = re.search(r"(?:type|write|input)\s+['\"]?([\s\S]+?)['\"]?$", user_prompt, re.IGNORECASE)
        if type_match:
            text_to_type = type_match.group(1).strip().strip("'\"")
            return {
                "thought": f"User requested typing text: '{text_to_type}'.",
                "tool": "automation.type_text",
                "params": {"text": text_to_type, "press_enter": True},
                "reply": f"Typing requested text into active window.",
            }

        # 8. WhatsApp Messaging
        wa_match = re.search(r"(?:whatsapp|message|send message to)\s+(?:number\s+)?([\+\d\s\-]+)\s+(?:saying|message|text)?\s*['\"]?([\s\S]+?)['\"]?$", user_prompt, re.IGNORECASE)
        if wa_match:
            phone = wa_match.group(1).strip()
            msg = wa_match.group(2).strip().strip("'\"")
            return {
                "thought": f"User requested WhatsApp dispatch to {phone}.",
                "tool": "automation.send_whatsapp_message",
                "params": {"phone_no": phone, "message": msg},
                "reply": f"Sending WhatsApp message to {phone}.",
            }

        # 9. Conversational default
        return {
            "thought": "Conversational query or unknown automation pattern.",
            "tool": "none",
            "params": {},
            "reply": f"I understand: '{user_prompt}'. As Ultron, I can create/move/delete files, capture screenshots, launch apps, or automate keyboard and mouse tasks for you.",
        }
