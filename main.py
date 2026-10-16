import os
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Voice-First AI Assistant API",
    description="FastAPI backend for Voice-First hackathon applications with conversation memory",
    version="1.0.0"
)

# Enable CORS for cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> list of message dicts
# Format: {"role": "user" | "assistant" | "system", "content": str, "timestamp": float}
sessions: Dict[str, List[Dict[str, any]]] = {}

SYSTEM_PROMPT = (
    "You are Jarvis, an ultra-fast, intelligent, voice-first AI assistant designed for live voice conversations. "
    "Keep answers conversational, engaging, and concise (1 to 3 sentences maximum), because your response "
    "will be read aloud using speech synthesis. Avoid markdown tables, bullet points, asterisks, or unpronounceable code snippets."
)

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user voice transcription or text message")
    session_id: Optional[str] = Field("default", description="Unique conversation session ID")

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    history_length: int

class ResetRequest(BaseModel):
    session_id: Optional[str] = "default"


def get_or_create_session(session_id: str) -> List[Dict[str, any]]:
    if session_id not in sessions:
        sessions[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT, "timestamp": time.time()}
        ]
    return sessions[session_id]


async def generate_response(history: List[Dict[str, any]]) -> str:
    """
    Generates response using OpenAI API, Gemini API, or an intelligent built-in fallback engine.
    This guarantees zero downtime during hackathon presentations even if API keys are missing.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    # 1. Try OpenAI if key is present
    if openai_key:
        try:
            messages = [{"role": m["role"], "content": m["content"]} for m in history]
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 150
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[OpenAI fallback] error: {e}")

    # 2. Try Gemini if key is present
    if gemini_key:
        try:
            # Build conversation turns for Gemini
            contents = []
            for m in history:
                if m["role"] == "user":
                    contents.append({"role": "user", "parts": [{"text": m["content"]}]})
                elif m["role"] == "assistant":
                    contents.append({"role": "model", "parts": [{"text": m["content"]}]})

            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(
                    url,
                    json={
                        "contents": contents,
                        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.7}
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception as e:
            print(f"[Gemini fallback] error: {e}")

    # 3. Built-in contextual AI Engine (Tracks context, personal details, memory, hackathon queries)
    last_user_msg = history[-1]["content"].lower().strip()
    
    # Check conversational history for context
    user_name = None
    for item in history:
        if item["role"] == "user":
            txt = item["content"].lower()
            if "my name is " in txt:
                user_name = item["content"].split("my name is", 1)[1].strip().split()[0].strip(".!?, ").title()
            elif "i am " in txt and "i am a" not in txt and "i am here" not in txt and "i am doing" not in txt:
                user_name = item["content"].split("i am", 1)[1].strip().split()[0].strip(".!?, ").title()

    # Dynamic contextual dialogue matching
    if any(q in last_user_msg for q in ["what is my name", "who am i", "do you remember my name"]):
        if user_name:
            return f"You told me your name is {user_name}! I remember our entire conversation."
        return "You haven't told me your name yet. What should I call you?"

    if "my name is" in last_user_msg:
        extracted = history[-1]["content"].split("name is", 1)[1].strip().split()[0].strip(".!?,")
        return f"Nice to meet you, {extracted.title()}! I have added that to our conversation memory. How can I assist your hackathon project today?"

    if any(q in last_user_msg for q in ["what can you do", "help", "who are you", "what is this app"]):
        return "I am Jarvis, your voice-first AI assistant! I listen to your speech in real time, remember our conversation history, and talk back using speech synthesis."

    if any(q in last_user_msg for q in ["how many messages", "history length", "conversation length"]):
        user_msgs = sum(1 for m in history if m["role"] == "user")
        return f"We have exchanged {user_msgs} messages in this active voice session, and I have stored every single turn."

    if any(q in last_user_msg for q in ["time", "what time is it"]):
        current_time = time.strftime("%I:%M %p")
        return f"The current time is {current_time}."

    if any(q in last_user_msg for q in ["hackathon", "pitch", "demo"]):
        return "For a winning hackathon pitch, show this hands-free voice loop in action: speak naturally, let me answer aloud, and highlight the zero-latency round trip!"

    if any(q in last_user_msg for q in ["hello", "hi", "hey", "good morning", "good evening"]):
        greeting = f"Hello {user_name}!" if user_name else "Hello there!"
        return f"{greeting} I'm online and listening. What would you like to explore?"

    # Contextual synthesis for general queries
    return f"I received: '{history[-1]['content']}'. Our session is active, conversation history is preserved, and voice roundtrip is operational. Connect an OPENAI_API_KEY in your .env file anytime for live LLM reasoning!"


@app.get("/")
def get_frontend():
    """Serves the voice frontend index.html directly from FastAPI."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Voice-First AI API is running. index.html not found in root directory."}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Primary endpoint for Voice-First AI interaction:
    1. Loads or initializes the conversation session.
    2. Stores the user's voice message in history.
    3. Generates conversational reply with session context.
    4. Appends assistant response to history.
    5. Returns clean response to be spoken aloud.
    """
    clean_msg = request.message.strip()
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    history = get_or_create_session(request.session_id)
    
    # Store user turn
    history.append({
        "role": "user",
        "content": clean_msg,
        "timestamp": time.time()
    })

    # Generate assistant reply
    reply = await generate_response(history)

    # Store assistant turn
    history.append({
        "role": "assistant",
        "content": reply,
        "timestamp": time.time()
    })

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        history_length=len(history)
    )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Returns conversation history for a given session."""
    if session_id not in sessions:
        return {"session_id": session_id, "messages": [], "count": 0}
    
    # Filter out system prompt for clean UI inspection
    clean_history = [
        {"role": m["role"], "content": m["content"], "timestamp": m.get("timestamp")}
        for m in sessions[session_id]
        if m["role"] != "system"
    ]
    return {
        "session_id": session_id,
        "messages": clean_history,
        "count": len(clean_history)
    }


@app.post("/reset")
def reset_history(request: ResetRequest):
    """Clears conversation history for the given session."""
    sid = request.session_id or "default"
    sessions[sid] = [
        {"role": "system", "content": SYSTEM_PROMPT, "timestamp": time.time()}
    ]
    return {"status": "success", "message": f"Session '{sid}' history reset.", "session_id": sid}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
