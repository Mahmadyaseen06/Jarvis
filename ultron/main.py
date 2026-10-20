"""
Ultron — Free Open-Source Local Desktop Automation Agent
Main CLI runner loop initializing .env, loading modular tools, and executing parsed LLM actions safely.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Load environment configuration (.env)
from dotenv import load_dotenv

# Ensure the project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Configure Unified Logging
LOG_DIR = PROJECT_ROOT / os.getenv("LOGS_DIR", "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "ultron.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ultron.main")

# Import Ultron Brain & Tool Dispatch Engine
from brain import UltronBrain
from tools import TOOL_DISPATCH, TOOL_CATALOG


def execute_action(action: Dict[str, Any], safe_mode: bool = True) -> Dict[str, Any]:
    """
    Safely executes a structured tool action produced by the LLM reasoning engine.
    
    Args:
        action: Dict containing 'tool', 'params', 'thought', and 'reply'.
        safe_mode: If True, requires user confirmation for destructive operations.
        
    Returns:
        Structured result dictionary.
    """
    tool_name = action.get("tool", "none")
    params = action.get("params", {}) or {}

    if tool_name == "none" or not tool_name:
        return {
            "success": True,
            "executed": False,
            "tool": "none",
            "message": "Conversational reply only; no desktop action required.",
        }

    handler = TOOL_DISPATCH.get(tool_name)
    if not handler:
        logger.error(f"Unrecognized tool requested: '{tool_name}'")
        return {
            "success": False,
            "executed": False,
            "tool": tool_name,
            "error": f"Tool '{tool_name}' is not registered in the Ultron tool dispatch engine.",
        }

    # Safety Guardrail: Prompt user before destructive or irreversible actions
    destructive_tools = {"file_manager.delete_item", "automation.send_whatsapp_message"}
    if safe_mode and tool_name in destructive_tools:
        print(f"\n⚠️  [SAFETY GUARD] Potentially destructive operation requested:")
        print(f"   Tool: {tool_name}")
        print(f"   Parameters: {params}")
        try:
            confirm = input("   Authorize execution? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                return {
                    "success": False,
                    "executed": False,
                    "tool": tool_name,
                    "message": "Operation cancelled by user.",
                }
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return {"success": False, "executed": False, "tool": tool_name, "message": "Cancelled"}

    # Execute tool with parameter forwarding
    try:
        start_time = time.time()
        logger.info(f"Executing '{tool_name}' with params: {params}")
        result = handler(**params)
        duration = round(time.time() - start_time, 3)
        result["duration_seconds"] = duration
        result["tool"] = tool_name
        return result
    except TypeError as te:
        logger.exception(f"Parameter mismatch for tool '{tool_name}': {te}")
        return {
            "success": False,
            "executed": False,
            "tool": tool_name,
            "error": f"Parameter mismatch: {te}",
        }
    except Exception as e:
        logger.exception(f"Unexpected error executing '{tool_name}': {e}")
        return {
            "success": False,
            "executed": False,
            "tool": tool_name,
            "error": str(e),
        }


def print_banner(brain: UltronBrain):
    """Displays the Ultron startup banner and active AI provider."""
    print("=" * 66)
    print(" ⚡ U L T R O N — Free Local Desktop Automation Agent")
    print("=" * 66)
    print(f" 🧠 AI Brain Provider: {brain.provider.upper()} ({brain.model_name})")
    print(f" 🛠️  Tools Loaded:     {len(TOOL_DISPATCH)} automated skills")
    print(f" 🛡️  Safe Mode:        {'ENABLED (Prompts for destructive actions)' if os.getenv('ULTRON_SAFE_MODE', 'true').lower() == 'true' else 'DISABLED'}")
    print(" Type 'help' for examples, 'tools' to list actions, or 'exit' to quit.")
    print("=" * 66 + "\n")


def print_help():
    """Prints helpful example prompts."""
    print("\n💡 Example Commands:")
    print("  • 'take a screenshot of my screen'")
    print("  • 'create a folder called Project_Ultron on my desktop'")
    print("  • 'create a file called notes.txt with content Hello World'")
    print("  • 'list all files on my desktop'")
    print("  • 'open Calculator app'")
    print("  • 'type Testing Ultron automation'")
    print("  • 'send a whatsapp message to +1234567890 saying Mission Ready'")
    print("  • 'delete folder Project_Ultron'")
    print()


def print_tools():
    """Prints the registered tool catalog."""
    print("\n📦 Registered Ultron Tools:")
    for t in TOOL_CATALOG:
        print(f"  • {t['name']}: {t['description']}")
    print()


def run_cli_loop():
    """Runs the interactive Read-Eval-Print loop for Ultron desktop automation."""
    brain = UltronBrain()
    safe_mode = os.getenv("ULTRON_SAFE_MODE", "true").lower() == "true"
    
    print_banner(brain)

    while True:
        try:
            user_input = input("Ultron > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Shutting down Ultron. Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "quit", "q"):
            print("👋 Ultron session terminated. Goodbye!")
            break
        elif cmd == "help":
            print_help()
            continue
        elif cmd == "tools":
            print_tools()
            continue
        elif cmd == "status":
            print(f"Brain: {brain.provider} ({brain.model_name}) | Safe Mode: {safe_mode}")
            continue

        # 1. AI Reasoning & Structured Command Generation
        print("🤔 Processing instruction...")
        action = brain.think(user_input)

        print(f"\n🧠 [Thought]: {action.get('thought')}")
        print(f"🤖 [Ultron]:  {action.get('reply')}")

        tool_name = action.get("tool", "none")
        if tool_name != "none":
            print(f"🔧 [Action]:  {tool_name} with {action.get('params', {})}")
            
            # 2. Safe Tool Execution
            res = execute_action(action, safe_mode=safe_mode)
            if res.get("success"):
                print(f"✅ [Result]:  {res.get('message', 'Execution successful')}\n")
            else:
                print(f"❌ [Error]:   {res.get('error', res.get('message', 'Execution failed'))}\n")
        else:
            print()




if __name__ == "__main__":
    # If arguments are passed on the command line (e.g. python main.py "take screenshot")
    if len(sys.argv) > 1 and sys.argv[1] not in ("--help", "-h"):
        inline_prompt = " ".join(sys.argv[1:])
        brain = UltronBrain()
        print(f"⚡ Ultron executing: '{inline_prompt}'")
        parsed_action = brain.think(inline_prompt)
        print(f"🧠 [Thought]: {parsed_action.get('thought')}")
        print(f"🤖 [Reply]:   {parsed_action.get('reply')}")
        if parsed_action.get("tool") != "none":
            exec_res = execute_action(parsed_action, safe_mode=False)
            print(f"⚡ [Result]:  {exec_res}")
    else:
        run_cli_loop()
