"""
Integration test suite for Jarvis Voice-First AI backend.
Validates health, HTML delivery, multi-turn conversation memory, and session reset.
Run with: python test_app.py
"""

from starlette.testclient import TestClient
from main import app

def run_tests():
    client = TestClient(app)
    session_id = "test-voice-session"

    print("=" * 60)
    print("🎙️ RUNNING JARVIS VOICE-FIRST INTEGRATION TESTS")
    print("=" * 60)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("✅ 1. /health endpoint: OK ->", res.json())

    # 2. Frontend HTML serving
    res = client.get("/")
    assert res.status_code == 200, f"Root endpoint failed: {res.text}"
    assert "JARVIS" in res.text
    assert "SpeechRecognition" in res.text
    assert "SpeechSynthesis" in res.text
    print(f"✅ 2. GET / (index.html): OK ({len(res.text)} bytes served)")

    # 3. First voice turn (User introduces themselves)
    res = client.post("/chat", json={
        "message": "Hi, my name is Jordan.",
        "session_id": session_id
    })
    assert res.status_code == 200, f"Turn 1 failed: {res.text}"
    data = res.json()
    print("✅ 3. POST /chat (Turn 1): User introduced name.")
    print(f"   AI Spoken Reply: \"{data['reply']}\"")
    assert "Jordan" in data["reply"]

    # 4. Multi-turn context memory check
    res = client.post("/chat", json={
        "message": "What is my name and who are you?",
        "session_id": session_id
    })
    assert res.status_code == 200, f"Turn 2 failed: {res.text}"
    data = res.json()
    print("✅ 4. POST /chat (Turn 2): Multi-turn context memory verified.")
    print(f"   AI Spoken Reply: \"{data['reply']}\"")
    assert "Jordan" in data["reply"]

    # 5. History endpoint verification
    res = client.get(f"/history/{session_id}")
    assert res.status_code == 200
    hist = res.json()
    print(f"✅ 5. GET /history/{session_id}: {hist['count']} messages preserved in active session.")
    assert hist["count"] == 4  # 2 user messages + 2 assistant replies

    # 6. Session reset
    res = client.post("/reset", json={"session_id": session_id})
    assert res.status_code == 200
    res_after = client.get(f"/history/{session_id}")
    assert res_after.json()["count"] == 0
    print("✅ 6. POST /reset: Session memory successfully cleared.")

    print("=" * 60)
    print("🎉 ALL TESTS PASSED! Voice-First stack is 100% verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
