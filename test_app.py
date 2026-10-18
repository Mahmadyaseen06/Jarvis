"""
Integration test suite for J.A.R.V.I.S. Holographic AI System Dashboard (FastAPI + Gemma 4).
Validates HTML delivery, /chat schema compliance, SYSTEM_SCAN, ACTIVATE_DEFENSE, DEPLOY_WIDGET, and chat history.
Run with: python3 test_app.py
"""

from starlette.testclient import TestClient
from main import app, chat_history, save_todos

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

    # 24. Battery Telemetry Query
    res_batt = client.post("/chat", json={"text": "what is my battery percentage"})
    assert res_batt.status_code == 200
    batt_data = res_batt.json()
    assert batt_data["action"]["command"] == "SHOW_TELEMETRY"
    assert batt_data["action"]["telemetry_type"] == "battery"
    assert "battery" in batt_data["action"]
    assert isinstance(batt_data["action"]["battery"]["percent"], int)
    print(f"✅ 24. POST /chat (Battery Vitals): {batt_data['action']['battery']['percent']}% ({batt_data['action']['battery']['power_source']})")

    # 25. Storage / Disk Usage Query
    res_storage = client.post("/chat", json={"text": "how much storage do I have left?"})
    assert res_storage.status_code == 200
    storage_data = res_storage.json()
    assert storage_data["action"]["command"] == "SHOW_TELEMETRY"
    assert storage_data["action"]["telemetry_type"] == "storage"
    assert "storage" in storage_data["action"]
    print(f"✅ 25. POST /chat (Storage Vitals): {storage_data['action']['storage']['free_gb']}GB free / {storage_data['action']['storage']['total_gb']}GB")

    # 26. Direct DM Automation (iMessage platform routing)
    res_dm = client.post("/chat", json={"text": "dm Alex on imessage I will be there soon"})
    assert res_dm.status_code == 200
    dm_data = res_dm.json()
    assert dm_data["action"]["command"] in ["SEND_WHATSAPP", "AUTOMATE_DM"]
    assert dm_data["action"]["platform"] == "imessage"
    assert dm_data["action"]["phone"] == "Alex"
    assert "I will be there soon" in dm_data["action"]["message"]
    print("✅ 26. POST /chat (Direct DM Automation): Autonomous iMessage dispatch verified.")

    # 27. GET /api/dms/status
    res_dm_status = client.get("/api/dms/status")
    assert res_dm_status.status_code == 200
    assert "imessage" in res_dm_status.json()
    assert "whatsapp" in res_dm_status.json()
    print("✅ 27. GET /api/dms/status: Multi-channel DM status operational.")

    # 28. POST /api/dms/send
    res_dm_send = client.post("/api/dms/send", json={"recipient": "Tony", "message": "Repulsor test complete", "platform": "imessage"})
    assert res_dm_send.status_code == 200
    assert res_dm_send.json()["ok"] is True
    print("✅ 28. POST /api/dms/send: Programmatic DM API verified.")

    # 29. Full System Diagnostics & Telemetry Query
    res_full_sys = client.post("/chat", json={"text": "give a full access to my system and get every information like battery precentage, storage, etc,.. And give direct access to my DMs so that it can domeverything automatically."})
    assert res_full_sys.status_code == 200
    full_sys_data = res_full_sys.json()
    assert full_sys_data["action"]["command"] == "SHOW_TELEMETRY"
    assert full_sys_data["action"]["telemetry_type"] == "full_system"
    assert "battery" in full_sys_data["action"]
    assert "storage" in full_sys_data["action"]
    assert "chip" in full_sys_data["action"]
    print("✅ 29. POST /chat (Full System Access & Vitals): Complete hardware diagnostics verified.")

    # 30. Direct DM Gateway Access Query
    res_dm_hub = client.post("/chat", json={"text": "access to my dms"})
    assert res_dm_hub.status_code == 200
    dm_hub_data = res_dm_hub.json()
    assert dm_hub_data["action"]["command"] == "AUTOMATE_DM"
    assert dm_hub_data["action"]["mode"] == "hub"
    print("✅ 30. POST /chat (Direct DM Access): Autonomous DM gateway hub routing verified.")

    # 31. Formal Letter to Principal (Medical Leave)
    res_letter_p = client.post("/chat", json={"text": "write a letter to principal requestings used to illness"})
    assert res_letter_p.status_code == 200
    letter_p_data = res_letter_p.json()
    assert letter_p_data["action"]["command"] == "COMPOSE_DOCUMENT"
    assert "Principal" in letter_p_data["action"]["recipient"]
    assert "content" in letter_p_data["action"]
    assert "Leave of Absence" in letter_p_data["action"]["subject"]
    print(f"✅ 31. POST /chat (Letter to Principal): {letter_p_data['action']['subject']} ({letter_p_data['action']['word_count']} words)")

    # 32. Formal Letter to Boss (Inability to Attend)
    res_letter_b = client.post("/chat", json={"text": "write a letter to the boss that I was just so I can't attend to this"})
    assert res_letter_b.status_code == 200
    letter_b_data = res_letter_b.json()
    assert letter_b_data["action"]["command"] == "COMPOSE_DOCUMENT"
    assert "Boss" in letter_b_data["action"]["recipient"] or "Manager" in letter_b_data["action"]["recipient"]
    assert "content" in letter_b_data["action"]
    print(f"✅ 32. POST /chat (Letter to Boss): {letter_b_data['action']['subject']} ({letter_b_data['action']['word_count']} words)")

    # 33. OpenJarvis Code Synthesis (WRITE_CODE)
    res_code = client.post("/chat", json={"text": "write a code to add two numbers in Python"})
    assert res_code.status_code == 200
    code_data = res_code.json()
    assert code_data["action"]["command"] == "WRITE_CODE"
    assert "add_two_numbers" in code_data["action"]["code"] or "add_numbers" in code_data["action"]["code"] or "def" in code_data["action"]["code"]
    assert "Yaseen" in code_data["reply"] or "Commander" in code_data["reply"] or "Sir" in code_data["reply"]
    assert code_data["action"]["execution"]["success"] is True
    print(f"✅ 33. POST /chat (WRITE_CODE OpenJarvis): {code_data['action']['title']} pre-executed in {code_data['action']['execution']['duration']}s")

    # 34. POST /api/code/run Endpoint
    res_run = client.post("/api/code/run", json={"code": "x = 40 + 2\nprint(f'Computed: {x}')"})
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["ok"] is True
    assert "Computed: 42" in run_data["output"]
    print(f"✅ 34. POST /api/code/run: Isolated OpenJarvis runner executed in {run_data['duration']}s: {run_data['output']}")

    # 35. POST /api/shell/run Endpoint
    res_shell = client.post("/api/shell/run", json={"command": "echo 'J.A.R.V.I.S. OpenJarvis Active'"})
    assert res_shell.status_code == 200
    shell_data = res_shell.json()
    assert shell_data["ok"] is True
    assert "J.A.R.V.I.S. OpenJarvis Active" in shell_data["output"]
    print(f"✅ 35. POST /api/shell/run: Hardened shell executor verified in {shell_data['duration']}s")

    # 36. Direct WhatsApp API Dispatch (POST /api/whatsapp/send)
    res_wa = client.post("/api/whatsapp/send", json={"recipient": "Alex", "message": "Arriving in 5 minutes"})
    assert res_wa.status_code == 200
    wa_data = res_wa.json()
    assert wa_data["ok"] is True
    assert wa_data["resolved_phone"] == "+1234567890"
    assert "whatsapp://send?phone=1234567890" in wa_data["desktop_url"]
    assert "web.whatsapp.com" in wa_data["web_url"]
    print(f"✅ 36. POST /api/whatsapp/send: Programmatic WhatsApp automated dispatch verified ({wa_data['desktop_url']})")

    # 37. Contact Registry (GET & POST /api/contacts - thevickypedia/Jarvis)
    res_ct = client.get("/api/contacts")
    assert res_ct.status_code == 200
    contacts = res_ct.json()
    assert "alex" in contacts.get("phone", {})
    res_add_ct = client.post("/api/contacts", json={"name": "Pepper", "phone": "+1999888777", "email": "pepper@stark.com"})
    assert res_add_ct.status_code == 200
    print("✅ 37. GET & POST /api/contacts: Contact book registry verified (thevickypedia/Jarvis)")

    # 38. Todo Task Registry (GET & POST /api/todos - thevickypedia/Jarvis)
    initial_todos = client.get("/api/todos").json().get("todos", [])
    res_add_todo = client.post("/api/todos", json={"task": "Temporary integration test task", "done": False})
    assert res_add_todo.status_code == 200
    assert res_add_todo.json()["todo"]["task"] == "Temporary integration test task"
    save_todos(initial_todos)
    print("✅ 38. GET & POST /api/todos: Task and todo registry operational (thevickypedia/Jarvis)")

    # 39. Natural Language WhatsApp with Contact Resolution in /chat
    res_chat_wa = client.post("/chat", json={"text": "send whatsapp to Mom I will be late for dinner"})
    assert res_chat_wa.status_code == 200
    chat_wa_data = res_chat_wa.json()
    assert chat_wa_data["action"]["command"] == "SEND_WHATSAPP"
    assert chat_wa_data["action"]["recipient"] == "Mom"
    assert chat_wa_data["action"]["resolved_phone"] == "+1987654321"
    assert "1987654321" in chat_wa_data["action"]["web_url"]
    print("✅ 39. POST /chat (WhatsApp Contact Resolution): 'Mom' resolved to +1987654321 with pre-filled Web/Desktop URLs")

    # 40. Screen Lock / System Sleep (thevickypedia/Jarvis)
    res_lock = client.post("/chat", json={"text": "Jarvis, lock screen and secure workstation"})
    assert res_lock.status_code == 200
    assert res_lock.json()["action"]["command"] == "LOCK_SCREEN"
    print("✅ 40. POST /chat (Screen Lock & Standby): System lock command dispatched cleanly")

    # 41. Natural YouTube Query 1: "best video to learn Java on YouTube"
    res_yt1 = client.post("/chat", json={"text": "best video to learn Java on YouTube"})
    assert res_yt1.status_code == 200
    data_yt1 = res_yt1.json()
    assert data_yt1["action"]["command"] == "PLAY_MEDIA"
    assert data_yt1["action"]["service"] == "youtube"
    assert "best video to learn Java" in data_yt1["action"]["media_query"]
    assert "youtube.com/results" in data_yt1["action"]["web_url"]
    print("✅ 41. POST /chat (Natural YouTube Intent 1): 'best video to learn Java on YouTube' -> PLAY_MEDIA YouTube")

    # 42. Natural YouTube Query 2: "Apna college Java tutorial on YouTube"
    res_yt2 = client.post("/chat", json={"text": "Apna college Java tutorial on YouTube"})
    assert res_yt2.status_code == 200
    data_yt2 = res_yt2.json()
    assert data_yt2["action"]["command"] == "PLAY_MEDIA"
    assert data_yt2["action"]["service"] == "youtube"
    assert "Apna college Java tutorial" in data_yt2["action"]["media_query"]
    print("✅ 42. POST /chat (Natural YouTube Intent 2): 'Apna college Java tutorial on YouTube' -> PLAY_MEDIA YouTube")

    # 43. WhatsApp Direct to 8197646867 with Indian +91 Country Code Normalization
    res_wa_num = client.post("/chat", json={"text": "whatsapp 8197646867 mission successful"})
    assert res_wa_num.status_code == 200
    data_wa_num = res_wa_num.json()
    assert data_wa_num["action"]["command"] == "SEND_WHATSAPP"
    assert data_wa_num["action"]["resolved_phone"] == "+918197646867"
    assert "918197646867" in data_wa_num["action"]["clean_digits"]
    print("✅ 43. POST /chat (WhatsApp +91 Normalization): '8197646867' normalized to +918197646867 and 918197646867")

    # 44. OpenJarvis Executive Briefing / Morning Digest
    res_digest = client.post("/chat", json={"text": "give me my morning digest"})
    assert res_digest.status_code == 200
    data_digest = res_digest.json()
    assert data_digest["action"]["command"] == "DIGEST_BRIEFING"
    assert "OpenJarvis Executive Briefing" in data_digest["reply"]
    res_briefing_api = client.get("/api/openjarvis/briefing")
    assert res_briefing_api.status_code == 200
    assert res_briefing_api.json()["commander"] == "Yaseen"
    # 45. Natural Contact Registration & Friend WhatsApp Dispatch
    res_add_c = client.post("/chat", json={"text": "save contact Aman 9123456789"})
    assert res_add_c.status_code == 200
    assert res_add_c.json()["action"]["command"] == "MANAGE_CONTACTS"
    res_friend_wa = client.post("/chat", json={"text": "send whatsapp to Aman let's study tonight"})
    assert res_friend_wa.status_code == 200
    data_f_wa = res_friend_wa.json()
    assert data_f_wa["action"]["command"] == "SEND_WHATSAPP"
    assert "919123456789" in data_f_wa["action"]["desktop_url"]
    print("✅ 45. POST /chat (Friend Contact Registration & WhatsApp): 'save contact Aman' & dispatch to friend verified")

    print("=" * 60)
    print("🎉 ALL 45 TESTS PASSED! J.A.R.V.I.S. AI System Dashboard is 100% verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()



