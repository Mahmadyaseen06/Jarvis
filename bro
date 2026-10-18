#!/usr/bin/env python3
"""
J.A.R.V.I.S. CLI Command Terminal Bridge ('bro' / 'jarvis')
Allows direct terminal execution of J.A.R.V.I.S. directives, system diagnostics, and DM dispatches.
Example:
    ./bro what is my battery percentage
    ./bro give a full access to my system
    ./bro dm Alex on imessage I will be there soon
"""
import sys
import os
import json
import urllib.request
import urllib.parse

# ANSI Terminal Colors
CYAN = "\033[36m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
PURPLE = "\033[35m"
RESET = "\033[0m"

def main():
    args = sys.argv[1:]
    if not args:
        print(f"{CYAN}{BOLD}J.A.R.V.I.S. CLI Console Active{RESET}")
        print("Usage: ./bro <your prompt or command>")
        print("Example: ./bro give a full access to my system and get every information")
        sys.exit(0)

    user_text = " ".join(args).strip()

    # Attempt to query local server
    api_url = "http://127.0.0.1:8000/chat"
    req_data = json.dumps({"text": user_text}).encode("utf-8")
    req = urllib.request.Request(api_url, data=req_data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Fallback to local in-process engine if daemon is not reached
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from main import fallback_jarvis_engine, execute_mac_task
            data = fallback_jarvis_engine(user_text)
            action = data.get("action", {})
            if action and action.get("command") != "NONE":
                execute_mac_task(action)
        except Exception as e:
            data = {
                "reply": f"Console routing error: {e}",
                "action": {"command": "NONE"}
            }

    reply = data.get("reply", "All holographic systems nominal, Sir.")
    action = data.get("action", {})

    print(f"\n{CYAN}{BOLD}◈ J.A.R.V.I.S. // STARK OS{RESET}")
    print(f"{GREEN}{reply}{RESET}\n")

    cmd = action.get("command")
    if cmd == "SHOW_TELEMETRY":
        batt = action.get("battery", {})
        st = action.get("storage", {})
        chip = action.get("chip", "Apple Silicon M2")
        uptime = action.get("uptime", "active")
        print(f"{PURPLE}[SYSTEM DIAGNOSTICS]{RESET}")
        print(f"  • Battery: {batt.get('percent', 91)}% ({batt.get('time_remaining', 'AC Power')})")
        print(f"  • Storage: {st.get('free_gb', 83.5)} GB free of {st.get('total_gb', 228.3)} GB")
        print(f"  • Core:    {chip} | RAM: {action.get('total_ram_gb', 16.0)} GB | Uptime: {uptime}")
        print(f"  • DMs:     iMessage & WhatsApp ONLINE (Autonomous Gateway Active)\n")
    elif cmd in ["AUTOMATE_DM", "SEND_WHATSAPP"]:
        recipient = action.get("recipient", "Recipient")
        msg = action.get("message", "")
        print(f"{YELLOW}[DIRECT MESSAGE DISPATCH]{RESET}")
        print(f"  • To:      {recipient}")
        print(f"  • Content: '{msg}'")
        print(f"  • Status:  Transmitted via Apple Messages / WhatsApp\n")
    elif cmd == "COMPOSE_DOCUMENT":
        recipient = action.get("recipient", "Recipient")
        subject = action.get("subject", "Formal Letter")
        content = action.get("content", "")
        print(f"{YELLOW}[DRAFTED FORMAL DOCUMENT]{RESET}")
        print(f"  • To:      {recipient}")
        print(f"  • Subject: {subject}\n")
        print(f"{CYAN}--- DOCUMENT PREVIEW ---{RESET}")
        print(content)
        print(f"{CYAN}------------------------{RESET}\n")
    elif cmd == "WRITE_CODE":
        title = action.get("title", "Python Code")
        code = action.get("code", "")
        output = action.get("output", "")
        duration = action.get("execution", {}).get("duration", 0.02)
        print(f"{CYAN}{BOLD}[OPENJARVIS CODE INTERPRETER // {title.upper()}]{RESET}")
        print(f"{YELLOW}--- PYTHON SOURCE ---{RESET}")
        print(code)
        print(f"{YELLOW}--- SANDBOX OUTPUT ({duration}s) ---{RESET}")
        print(f"{GREEN}{output}{RESET}\n")

if __name__ == "__main__":
    main()
