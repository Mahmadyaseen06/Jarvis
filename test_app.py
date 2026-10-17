"""
Integration test suite for J.A.R.V.I.S. Holographic AI System Dashboard (FastAPI + Gemma 4).
Validates HTML delivery, /chat schema compliance, SYSTEM_SCAN, ACTIVATE_DEFENSE, DEPLOY_WIDGET, and chat history.
Run with: python3 test_app.py
"""

from starlette.testclient import TestClient
from main import app, chat_history

def run_tests():
    client = TestClient(app)
    chat_history.clear()

    print("=" * 60)
    print("🤖 RUNNING J.A.R.V.I.S. HOLOGRAPHIC DASHBOARD INTEGRATION TESTS")
    print("=" * 60)

    # 1. Frontend HTML serving
    res = client.get("/")
    assert res.status_code == 200, f"Root endpoint failed: {res.text}"
    assert "J.A.R.V.I.S." in res.text or "JARVIS" in res.text
    print(f"✅ 1. GET / (index.html): OK ({len(res.text)} bytes served)")

    # 2. SYSTEM_SCAN Command
    res = client.post("/chat", json={"text": "Jarvis, run a full system scan and check diagnostics"})
    assert res.status_code == 200, f"SYSTEM_SCAN failed: {res.text}"
    data = res.json()
    print("✅ 2. POST /chat (SYSTEM_SCAN):", data)
    assert "reply" in data and len(data["reply"]) > 0
    assert data["action"]["command"] == "SYSTEM_SCAN"

    # 3. ACTIVATE_DEFENSE Command
    res = client.post("/chat", json={"text": "Engage combat mode and activate defense protocols"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 3. POST /chat (ACTIVATE_DEFENSE):", data)
    assert data["action"]["command"] == "ACTIVATE_DEFENSE"

    # 4. DEPLOY_WIDGET Command
    res = client.post("/chat", json={"text": "Deploy widget Arc Reactor Thermal Output"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 4. POST /chat (DEPLOY_WIDGET):", data)
    assert data["action"]["command"] == "DEPLOY_WIDGET"
    assert "widget_name" in data["action"] and len(data["action"]["widget_name"]) > 0

    # 5. NONE (Conversational chat)
    res = client.post("/chat", json={"text": "Hello Jarvis, tell me a quick witty remark"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 5. POST /chat (NONE / Chatting):", data)
    assert data["action"]["command"] == "NONE"

    # 6. Check History
    res = client.get("/history")
    assert res.status_code == 200
    hist = res.json()
    print(f"✅ 6. GET /history: {hist['count']} messages preserved in context.")
    assert hist["count"] == 8  # 4 user + 4 assistant

    # 7. Clear History
    res = client.post("/clear")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"
    res_after = client.get("/history")
    assert res_after.json()["count"] == 0
    print("✅ 7. POST /clear: Context memory successfully purged.")

    print("=" * 60)
    print("🎉 ALL TESTS PASSED! J.A.R.V.I.S. AI System Dashboard is 100% verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
