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
    title="Voice-Controlled AI Task Board",
    description="Kanban project manager powered by FastAPI and Google Gemma 4"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global chat history list to store conversational context
chat_history: List[Dict[str, str]] = []

# Exact system prompt requested by the user
SYSTEM_PROMPT = (
    "You are an AI project manager. Remember the conversation context. "
    "You must ALWAYS respond with raw JSON containing exactly two keys: 'reply' "
    "(a short spoken confirmation) and 'action'. The 'action' key must be an object "
    "with 'command' (choose one: ADD_TASK, MOVE_TASK, CLEAR_ALL, or NONE). "
    "If ADD_TASK, include 'task_name' and 'priority' (High/Low). "
    "If MOVE_TASK, include 'task_name' and 'new_status' (Todo, InProgress, Done)."
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
        "reply": raw_text.replace("{", "").replace("}", "").strip() or "Task received.",
        "action": {"command": "NONE"}
    }


def fallback_pm_engine(user_text: str) -> Dict[str, Any]:
    """Rule-based PM fallback to ensure the app works immediately if GEMMA_API_KEY is not set."""
    lower = user_text.lower().strip()

    # CLEAR_ALL command
    if any(k in lower for k in ["clear all", "clear board", "empty board", "delete all", "reset board"]):
        return {
            "reply": "Clearing all tasks from the task board.",
            "action": {"command": "CLEAR_ALL"}
        }

    # MOVE_TASK command (e.g. "Move landing page to In Progress" or "Move auth to Done")
    move_match = re.search(r"move\s+(?:the\s+)?(.+?)\s+to\s+(todo|to-do|in\s*progress|done)", lower)
    if move_match:
        raw_name = move_match.group(1).strip()
        raw_status = move_match.group(2).replace(" ", "").replace("-", "")

        status_map = {
            "todo": "Todo",
            "inprogress": "InProgress",
            "done": "Done"
        }
        new_status = status_map.get(raw_status, "InProgress")
        clean_task = raw_name.replace("task", "").strip().title()

        return {
            "reply": f"Moved '{clean_task}' to {new_status}.",
            "action": {
                "command": "MOVE_TASK",
                "task_name": clean_task,
                "new_status": new_status
            }
        }

    # ADD_TASK command (e.g. "Add task build landing page priority high")
    if any(k in lower for k in ["add", "create", "new task", "put"]):
        priority = "High" if any(p in lower for p in ["high", "urgent", "critical", "important"]) else "Low"
        
        # Clean task name extraction
        cleaned_name = user_text
        for prefix in ["add task", "add a task", "add", "create task", "create a task", "create", "new task"]:
            if lower.startswith(prefix):
                cleaned_name = user_text[len(prefix):].strip()
                break
        
        # Strip priority indicators from name
        cleaned_name = re.sub(r"(?i)\s+priority\s+(high|low)", "", cleaned_name)
        cleaned_name = re.sub(r"(?i)\s+with\s+(high|low)\s+priority", "", cleaned_name)
        cleaned_name = re.sub(r"(?i)\s+(high|low)\s+priority", "", cleaned_name)
        cleaned_name = cleaned_name.strip(" .:!?,") or "New Task"
        task_name = cleaned_name[:50].title()

        return {
            "reply": f"Added '{task_name}' to To Do with {priority} priority.",
            "action": {
                "command": "ADD_TASK",
                "task_name": task_name,
                "priority": priority
            }
        }

    return {
        "reply": f"I heard: '{user_text}'. Tell me to add a task, move a task, or clear the board.",
        "action": {"command": "NONE"}
    }


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
    - Calls google/gemma-4-instruct via InferenceClient.
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

    # 2. Call google/gemma-4-instruct via InferenceClient if key is configured
    if api_key:
        try:
            client = InferenceClient(token=api_key)

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
            print(f"[Gemma InferenceClient Warning]: {e}")
            response_data = fallback_pm_engine(user_text)
    else:
        # Fast local fallback ensuring immediate offline functionality
        response_data = fallback_pm_engine(user_text)

    # Validate action object and command
    if not isinstance(response_data.get("action"), dict):
        response_data["action"] = {"command": "NONE"}

    valid_commands = {"ADD_TASK", "MOVE_TASK", "CLEAR_ALL", "NONE"}
    if response_data["action"].get("command") not in valid_commands:
        response_data["action"]["command"] = "NONE"

    if "reply" not in response_data:
        response_data["reply"] = "Board updated."

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
