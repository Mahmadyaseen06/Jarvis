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

# Iron Man J.A.R.V.I.S. AI persona system prompt
SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the sophisticated AI assistant created by Tony Stark. "
    "You speak with calm British elegance, witty politeness, and respectful loyalty, addressing the user as 'Sir'. "
    "You are currently managing the Stark Industries project directive board. "
    "Remember the conversation context. You must ALWAYS respond with raw JSON containing exactly two keys: "
    "'reply' (a crisp, courteous spoken response in classic J.A.R.V.I.S. character, e.g. 'Right away, Sir. Added to the directive queue.', 'Protocol completed, Sir.') "
    "and 'action'. The 'action' key must be an object with 'command' (choose one: ADD_TASK, MOVE_TASK, CLEAR_ALL, or NONE). "
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
        "reply": raw_text.replace("{", "").replace("}", "").strip() or "Understood, Sir. Protocol updated.",
        "action": {"command": "NONE"}
    }


def fallback_pm_engine(user_text: str) -> Dict[str, Any]:
    """Rule-based J.A.R.V.I.S. engine ensuring instant offline operation with full persona."""
    lower = user_text.lower().strip()

    # CLEAR_ALL command (e.g. "Clear the board", "Clear all tasks", "Reset board")
    if (
        re.search(r"\bclear\b.*\b(all|board|tasks?)\b", lower)
        or re.search(r"\b(reset|empty|purge)\b.*\bboard\b", lower)
        or any(k in lower for k in ["clear all", "clear board", "empty board", "delete all", "reset board", "clear tasks", "purge board"])
    ):
        return {
            "reply": "Clearing all directives from the Stark tactical display, Sir.",
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

        if new_status == "Done":
            reply_msg = f"Protocol '{clean_task}' marked as accomplished, Sir. Outstanding work."
        elif new_status == "InProgress":
            reply_msg = f"Commencing operation on '{clean_task}', Sir. Updating status to In Progress."
        else:
            reply_msg = f"Re-queueing '{clean_task}' into the backlog, Sir."

        return {
            "reply": reply_msg,
            "action": {
                "command": "MOVE_TASK",
                "task_name": clean_task,
                "new_status": new_status
            }
        }

    # Natural Language Shortcut: Complete / Finish / Mark as Done
    done_match = re.search(r"^(?:mark\s+(?:the\s+)?(.+?)\s+as\s+done|complete\s+(?:the\s+)?(.+)|finish\s+(?:the\s+)?(.+))$", lower)
    if done_match:
        raw_name = (done_match.group(1) or done_match.group(2) or done_match.group(3) or "").strip()
        clean_task = re.sub(r"(?i)\btask\b", "", raw_name).strip().title()
        if clean_task:
            return {
                "reply": f"Directive '{clean_task}' completed, Sir. Logging into archives.",
                "action": {
                    "command": "MOVE_TASK",
                    "task_name": clean_task,
                    "new_status": "Done"
                }
            }

    # Natural Language Shortcut: Start working on / Work on
    start_match = re.search(r"^(?:start\s+(?:working\s+on\s+)?(?:the\s+)?(.+)|begin\s+(?:working\s+on\s+)?(?:the\s+)?(.+))$", lower)
    if start_match:
        raw_name = (start_match.group(1) or start_match.group(2) or "").strip()
        clean_task = re.sub(r"(?i)\btask\b", "", raw_name).strip().title()
        if clean_task and not lower.startswith("start over"):
            return {
                "reply": f"Understood, Sir. Initializing active protocol for '{clean_task}'.",
                "action": {
                    "command": "MOVE_TASK",
                    "task_name": clean_task,
                    "new_status": "InProgress"
                }
            }

    # ADD_TASK command (e.g. "Add task build landing page priority high")
    if any(k in lower for k in ["add", "create", "new task", "put", "log task", "initialize task"]):
        priority = "High" if any(p in lower for p in ["high", "urgent", "critical", "important", "vital"]) else "Low"
        
        # Clean task name extraction
        cleaned_name = user_text
        for prefix in [
            "initialize task", "log task to", "log task",
            "add a task to", "add task to", "add a task", "add task",
            "create a task to", "create task to", "create a task", "create task",
            "add", "create", "new task"
        ]:
            if lower.startswith(prefix):
                cleaned_name = user_text[len(prefix):].strip()
                break
        
        # Strip priority indicators from name
        cleaned_name = re.sub(r"(?i)\s+priority\s+(high|low)", "", cleaned_name)
        cleaned_name = re.sub(r"(?i)\s+with\s+(high|low)\s+priority", "", cleaned_name)
        cleaned_name = re.sub(r"(?i)\s+(high|low)\s+priority", "", cleaned_name)
        cleaned_name = cleaned_name.strip(" .:!?,") or "New Directive"
        task_name = cleaned_name[:50].title()

        return {
            "reply": f"Right away, Sir. Added '{task_name}' to the backlog with {priority} priority.",
            "action": {
                "command": "ADD_TASK",
                "task_name": task_name,
                "priority": priority
            }
        }

    # Default Jarvis conversational reply
    if any(k in lower for k in ["hello", "hi", "hey", "jarvis", "who are you", "status"]):
        return {
            "reply": "Good day, Sir. J.A.R.V.I.S. online and standing by for your directives.",
            "action": {"command": "NONE"}
        }

    return {
        "reply": f"I hear you, Sir: '{user_text}'. Ready to catalog directives or adjust board protocols at your command.",
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
