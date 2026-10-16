"""
Integration test suite for Voice-Controlled AI Task Board backend (FastAPI + Gemma 4).
Validates HTML delivery, /chat schema compliance, task creation, movement, clearing, and history.
Run with: python3 test_app.py
"""

from starlette.testclient import TestClient
from main import app, chat_history

def run_tests():
    client = TestClient(app)
    chat_history.clear()

    print("=" * 60)
    print("📋 RUNNING VOICE-CONTROLLED AI TASK BOARD INTEGRATION TESTS")
    print("=" * 60)

    # 1. Frontend HTML serving
    res = client.get("/")
    assert res.status_code == 200, f"Root endpoint failed: {res.text}"
    assert "Voice-Controlled AI Task Board" in res.text or "AI Task Board" in res.text
    assert "SpeechRecognition" in res.text or "webkitSpeechRecognition" in res.text
    print(f"✅ 1. GET / (index.html): OK ({len(res.text)} bytes served)")

    # 2. Add Task (High Priority)
    res = client.post("/chat", json={"text": "Add a task to Build Authentication API with high priority"})
    assert res.status_code == 200, f"Add task failed: {res.text}"
    data = res.json()
    print("✅ 2. POST /chat (ADD_TASK):", data)
    assert "reply" in data and len(data["reply"]) > 0
    assert data["action"]["command"] == "ADD_TASK"
    assert data["action"]["priority"] == "High"
    assert "Authentication" in data["action"]["task_name"]

    # 3. Add Task (Low Priority)
    res = client.post("/chat", json={"text": "Add task Update footer documentation with low priority"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 3. POST /chat (ADD_TASK Low):", data)
    assert data["action"]["command"] == "ADD_TASK"
    assert data["action"]["priority"] == "Low"

    # 4. Move Task to InProgress
    res = client.post("/chat", json={"text": "Move Authentication API to In Progress"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 4. POST /chat (MOVE_TASK to InProgress):", data)
    assert data["action"]["command"] == "MOVE_TASK"
    assert data["action"]["new_status"] == "InProgress"

    # 5. Move Task to Done
    res = client.post("/chat", json={"text": "Move Authentication API to Done"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 5. POST /chat (MOVE_TASK to Done):", data)
    assert data["action"]["command"] == "MOVE_TASK"
    assert data["action"]["new_status"] == "Done"

    # 6. Clear All Tasks
    res = client.post("/chat", json={"text": "Clear the task board"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 6. POST /chat (CLEAR_ALL):", data)
    assert data["action"]["command"] == "CLEAR_ALL"

    # 7. Check History
    res = client.get("/history")
    assert res.status_code == 200
    hist = res.json()
    print(f"✅ 7. GET /history: {hist['count']} conversation messages tracked.")
    assert hist["count"] >= 10

    # 8. Clear History
    res = client.post("/clear")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"
    res_after = client.get("/history")
    assert res_after.json()["count"] == 0
    print("✅ 8. POST /clear: Chat history successfully reset.")

    print("=" * 60)
    print("🎉 ALL TESTS PASSED! AI Task Board stack is 100% verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
