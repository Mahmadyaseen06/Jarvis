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
    title="Gemma Restaurant Voice Assistant",
    description="Voice-First AI Restaurant Assistant powered by Gemma and FastAPI"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global chat history list to store conversation context
chat_history: List[Dict[str, str]] = []

SYSTEM_PROMPT = (
    "You are a fast, intelligent voice assistant for a restaurant. "
    "Remember the context of the conversation. "
    "You must ALWAYS respond with raw JSON containing exactly two keys: "
    "'reply' (a short, friendly conversational response to speak out loud) and "
    "'action' (choose exactly one: ADD_PIZZA, ADD_BURGER, CLEAR_CART, or NONE)."
)

class ChatInput(BaseModel):
    text: str


def extract_json(raw_text: str) -> Dict[str, Any]:
    """Extract and parse JSON from model output, handling optional markdown code fences."""
    cleaned = raw_text.strip()
    # Remove markdown code block fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Regex search for { ... } block
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback structure if parsing fails
    return {
        "reply": raw_text.replace("{", "").replace("}", "").strip() or "I received your order!",
        "action": "NONE"
    }


def fallback_restaurant_engine(user_text: str, history: List[Dict[str, str]]) -> Dict[str, str]:
    """Resilient fallback engine ensuring demo works if GEMMA_API_KEY is omitted or offline."""
    lower = user_text.lower()

    if any(w in lower for w in ["clear", "reset", "empty", "cancel", "start over"]):
        return {
            "reply": "I have cleared everything from your cart. What else would you like to order?",
            "action": "CLEAR_CART"
        }
    elif any(w in lower for w in ["pizza", "slice", "pie", "pepperoni", "margherita"]):
        return {
            "reply": "Adding a hot, delicious pizza to your cart!",
            "action": "ADD_PIZZA"
        }
    elif any(w in lower for w in ["burger", "cheeseburger", "patty", "hamburger"]):
        return {
            "reply": "You got it! Adding a juicy burger to your order.",
            "action": "ADD_BURGER"
        }
    elif any(w in lower for w in ["hello", "hi", "hey"]):
        return {
            "reply": "Welcome to our restaurant! Would you like a fresh pizza or a delicious burger today?",
            "action": "NONE"
        }
    elif any(w in lower for w in ["menu", "what do you have", "what can i order"]):
        return {
            "reply": "We specialize in fresh artisan pizzas and handcrafted burgers. Which would you like to start with?",
            "action": "NONE"
        }
    else:
        return {
            "reply": f"Sure thing! I noted: {user_text}. Would you like a pizza or a burger with that?",
            "action": "NONE"
        }


@app.get("/")
def serve_index():
    """Serve the index.html frontend."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "index.html not found"}


@app.post("/chat")
def chat_endpoint(payload: ChatInput):
    """
    POST /chat:
    1. Appends user text to chat_history.
    2. Calls google/gemma-4-instruct via InferenceClient.
    3. Parses the structured JSON response {'reply': ..., 'action': ...}.
    4. Appends assistant response to history and returns to client.
    """
    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # 1. Append user text to global chat history
    chat_history.append({"role": "user", "content": user_text})

    # Read GEMMA_API_KEY (or fallback HF_TOKEN)
    api_key = os.getenv("GEMMA_API_KEY") or os.getenv("HF_TOKEN")

    response_data = None

    # 2. Call google/gemma-4-instruct via HuggingFace InferenceClient if key is present
    if api_key:
        try:
            client = InferenceClient(token=api_key)

            # Build messages starting with system prompt followed by conversation history
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(chat_history)

            # Request completion from Gemma
            response = client.chat_completion(
                model="google/gemma-4-instruct",
                messages=messages,
                max_tokens=200,
                temperature=0.2
            )

            raw_reply = response.choices[0].message.content
            response_data = extract_json(raw_reply)

        except Exception as e:
            print(f"[Gemma InferenceClient Warning]: {e}")
            # Fall back smoothly if remote model is loading or key is invalid
            response_data = fallback_restaurant_engine(user_text, chat_history)
    else:
        # Seamless local fallback for instant zero-dependency testing
        response_data = fallback_restaurant_engine(user_text, chat_history)

    # Validate action key exists and is one of the allowed choices
    valid_actions = {"ADD_PIZZA", "ADD_BURGER", "CLEAR_CART", "NONE"}
    if response_data.get("action") not in valid_actions:
        response_data["action"] = "NONE"

    if "reply" not in response_data:
        response_data["reply"] = "Order updated!"

    # 3. Append assistant reply to chat history
    chat_history.append({"role": "assistant", "content": response_data["reply"]})

    # 4. Return the structured JSON to the client
    return response_data


@app.get("/history")
def get_history():
    """Retrieve the full global chat history."""
    return {"history": chat_history, "count": len(chat_history)}


@app.post("/clear")
def clear_history():
    """Clear conversation history."""
    global chat_history
    chat_history.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
