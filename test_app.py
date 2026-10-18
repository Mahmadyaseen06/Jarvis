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

    # 5. OPEN_APP Command
    res = client.post("/chat", json={"text": "Jarvis, open Notes app"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 5. POST /chat (OPEN_APP):", data)
    assert data["action"]["command"] == "OPEN_APP"

    # 6. SET_VOLUME Command
    res = client.post("/chat", json={"text": "Jarvis, set volume to 50"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 6. POST /chat (SET_VOLUME):", data)
    assert data["action"]["command"] == "SET_VOLUME"
    assert data["action"]["volume"] == 50

    # 7. SEND_WHATSAPP Command
    res = client.post("/chat", json={"text": "Jarvis, send a WhatsApp message to Alex saying I will arrive at 7 PM"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 7. POST /chat (SEND_WHATSAPP):", data)
    assert data["action"]["command"] == "SEND_WHATSAPP"
    assert "web_url" in data["action"]

    # 8. SEND_EMAIL Command
    res = client.post("/chat", json={"text": "Jarvis, send email to boss@stark.com with subject Status and body All systems nominal"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 8. POST /chat (SEND_EMAIL):", data)
    assert data["action"]["command"] == "SEND_EMAIL"
    assert "gmail_url" in data["action"]

    # 9. CALCULATE Command
    res = client.post("/chat", json={"text": "calculate 26 * 25"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 9. POST /chat (CALCULATE):", data)
    assert data["action"]["command"] == "CALCULATE"
    assert data["action"]["answer"] == "650"
    assert "Calculator" in data["action"].get("app_name", "")

    # 9b. Human Desktop Automation (Open calculator and type calculation)
    res = client.post("/chat", json={"text": "open calculator and type the calculation then execute"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 9b. POST /chat (HUMAN CALCULATOR):", data)
    assert data["action"]["command"] == "CALCULATE"
    assert "Calculator" in data["action"].get("app_name", "")
    assert data["action"].get("mode") == "human_desktop_simulation"
    assert "keystroke_sequence" in data["action"]

    # 10. FIND_FILE Command
    res = client.post("/chat", json={"text": "Jarvis, find file main.py in system"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 10. POST /chat (FIND_FILE):", data)
    assert data["action"]["command"] == "FIND_FILE"

    # 11. Flexible WhatsApp & Gmail variations
    res = client.post("/chat", json={"text": "send message on whatsapp to Pepper saying meeting rescheduled"})
    assert res.status_code == 200
    data = res.json()
    print("DEBUG TEST 11 data:", data)
    assert data["action"]["command"] == "SEND_WHATSAPP"
    assert "Pepper" in str(data["action"])
    assert "meeting" in str(data["action"]).lower()
    print("✅ 11. POST /chat (Flexible WhatsApp):", data)

    # 11b. Automated messaging just by saying contact name
    res = client.post("/chat", json={"text": "message Alex I will arrive at 7 PM"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 11b. POST /chat (Automated Message by Name):", data)
    assert data["action"]["command"] == "SEND_WHATSAPP"
    assert data["action"]["phone"] == "Alex"
    assert "7 PM" in data["action"]["message"]
    assert data["action"].get("auto_sent") == True

    # 12. NONE (Conversational chat)
    res = client.post("/chat", json={"text": "Hello Jarvis, tell me a quick witty remark"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 12. POST /chat (NONE / Chatting):", data)
    assert data["action"]["command"] == "NONE"

    # 13. Check History
    res = client.get("/history")
    assert res.status_code == 200
    hist = res.json()
    print(f"✅ 13. GET /history: {hist['count']} messages preserved in context.")
    assert hist["count"] == 26  # 13 user + 13 assistant

    # 7. Clear History
    res = client.post("/clear")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"
    res_after = client.get("/history")
    assert res_after.json()["count"] == 0
    print("✅ 7. POST /clear: Context memory successfully purged.")

    # 14. Transcribe Endpoint (Local Faster-Whisper)
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00' * 16000)
    buf.seek(0)
    res = client.post("/api/transcribe", files={"audio": ("test.wav", buf, "audio/wav")})
    assert res.status_code == 200
    assert "text" in res.json()
    print("✅ 14. POST /api/transcribe: Local Faster-Whisper audio transcription verified.")

    # 15. PLAY_MEDIA Command (Spotify & YouTube)
    res = client.post("/chat", json={"text": "Jarvis, play Bohemian Rhapsody on Spotify"})
    assert res.status_code == 200
    data = res.json()
    print("✅ 15. POST /chat (PLAY_MEDIA Spotify):", data)
    assert data["action"]["command"] == "PLAY_MEDIA"
    assert data["action"]["service"] == "spotify"
    assert "Bohemian Rhapsody" in data["action"]["media_query"]
    assert "spotify" in data["action"].get("desktop_url", "").lower() or "spotify" in data["action"].get("web_url", "").lower()

    res_yt = client.post("/chat", json={"text": "play interstellar soundtrack on youtube"})
    assert res_yt.status_code == 200
    data_yt = res_yt.json()
    print("✅ 15b. POST /chat (PLAY_MEDIA YouTube):", data_yt)
    assert data_yt["action"]["command"] == "PLAY_MEDIA"
    assert data_yt["action"]["service"] == "youtube"
    assert "interstellar" in data_yt["action"]["media_query"].lower()

    # 16. ACTIVATE_CAMERA Command
    res_cam = client.post("/chat", json={"text": "activate camera and run optical scan"})
    assert res_cam.status_code == 200
    data_cam = res_cam.json()
    print("✅ 16. POST /chat (ACTIVATE_CAMERA):", data_cam)
    assert data_cam["action"]["command"] == "ACTIVATE_CAMERA"
    assert data_cam["action"].get("open_hud_camera") is True

    # 17. 4-Tier Cognitive Brain & Goal Queue
    res_brain = client.get("/api/brain")
    assert res_brain.status_code == 200
    brain_data = res_brain.json()
    assert "identity" in brain_data
    assert "working_memory" in brain_data
    assert "episodic_memory" in brain_data
    assert "goal_queue" in brain_data
    print(f"✅ 17. GET /api/brain: 4-Tier Memory operational (Episodic count: {len(brain_data['episodic_memory'])})")

    res_goal = client.post("/api/brain/goal", json={"title": "Calibrate repulsor field output"})
    assert res_goal.status_code == 200
    assert res_goal.json()["ok"] is True
    print("✅ 17b. POST /api/brain/goal: Successfully enqueued cognitive directive.")

    # 18. Emergency Protocol Zero
    res_p0 = client.post("/api/protocol-zero")
    assert res_p0.status_code == 200
    assert res_p0.json()["status"] == "aborted"
    print("✅ 18. POST /api/protocol-zero: Emergency halt executed cleanly.")

    # 19. Hardware Vitals Telemetry
    res_vitals = client.get("/api/vitals")
    assert res_vitals.status_code == 200
    vitals_data = res_vitals.json()
    assert "cpu_percent" in vitals_data
    assert "total_ram_gb" in vitals_data
    assert "platform" in vitals_data
    print(f"✅ 19. GET /api/vitals: {vitals_data['platform']} CPU: {vitals_data['cpu_percent']}% RAM: {vitals_data['total_ram_gb']}GB")

    # 20. Identity Query ("what is your name" should NOT trigger CALCULATE)
    res_identity = client.post("/chat", json={"text": "what is your name?"})
    assert res_identity.status_code == 200
    identity_data = res_identity.json()
    assert identity_data["action"]["command"] == "NONE"
    assert "J.A.R.V.I.S." in identity_data["reply"]
    print("✅ 20. POST /chat (Identity): Clean identity response, no false calculation trap.")

    # 21. Time Query ("what time is it" should NOT trigger CALCULATE)
    res_time = client.post("/chat", json={"text": "what time is it?"})
    assert res_time.status_code == 200
    time_data = res_time.json()
    assert time_data["action"]["command"] == "NONE"
    assert "time is" in time_data["reply"]
    print("✅ 21. POST /chat (Time Check): Chronological response verified.")

    # 22. Direct Web Target ("open youtube" should route to OPEN_URL, not OPEN_APP)
    res_web = client.post("/chat", json={"text": "open youtube"})
    assert res_web.status_code == 200
    web_data = res_web.json()
    assert web_data["action"]["command"] == "OPEN_URL"
    assert "youtube.com" in web_data["action"]["url"]
    print("✅ 22. POST /chat (Web Target): Direct site launcher to OPEN_URL verified.")

    # 23. Safe Conversational Query with 'find' ("can you find a good joke" should NOT trigger FIND_FILE)
    res_joke = client.post("/chat", json={"text": "can you find a good joke"})
    assert res_joke.status_code == 200
    joke_data = res_joke.json()
    assert joke_data["action"]["command"] == "NONE"
    print("✅ 23. POST /chat (Conversational 'find'): Safe non-file intent preserved.")

    print("=" * 60)
    print("🎉 ALL TESTS PASSED! J.A.R.V.I.S. AI System Dashboard is 100% verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()



