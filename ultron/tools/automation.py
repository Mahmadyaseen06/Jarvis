"""
Ultron Automation Module
Safe, defensive wrappers for PyAutoGUI keyboard/mouse interactions, system shortcuts,
app launching, and WhatsApp messaging via pywhatkit.
Enforces strict PyAutoGUI safety rails (FAILSAFE=True, PAUSE=0.5s).
"""

import os
import sys
import time
import logging
import subprocess
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("ultron.tools.automation")

# Defensive import for PyAutoGUI
try:
    import pyautogui
    # Critical safety controls:
    # 1. FAILSAFE: Moving mouse cursor to any corner of the screen immediately aborts execution
    pyautogui.FAILSAFE = True
    # 2. PAUSE: Adds a mandatory 0.5s delay after every PyAutoGUI action to allow visual feedback
    pyautogui.PAUSE = 0.5
    PYAUTOGUI_AVAILABLE = True
except Exception as e:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
    logger.warning(f"PyAutoGUI initialization failed or not installed: {e}. Native system fallback active.")

# Defensive import for pywhatkit
try:
    import pywhatkit
    PYWHATKIT_AVAILABLE = True
except Exception as e:
    pywhatkit = None
    PYWHATKIT_AVAILABLE = False
    logger.info(f"pywhatkit not installed: {e}. Native browser/AppleScript fallback active.")


def get_screen_geometry() -> Dict[str, Any]:
    """Retrieves current screen resolution in pixels."""
    if PYAUTOGUI_AVAILABLE and pyautogui is not None:
        try:
            width, height = pyautogui.size()
            return {"success": True, "width": width, "height": height}
        except Exception as e:
            logger.warning(f"Failed to get screen size from pyautogui: {e}")
    
    # macOS system_profiler / fallback
    return {"success": True, "width": 1920, "height": 1080, "note": "default geometry"}


def move_cursor(x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
    """
    Safely moves the mouse cursor to the given coordinate.
    
    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        duration: Time in seconds for the movement animation.
        
    Returns:
        Structured result dict.
    """
    logger.info(f"Moving cursor to ({x}, {y}) over {duration}s")
    if not PYAUTOGUI_AVAILABLE or pyautogui is None:
        return {
            "success": False,
            "action": "move_cursor",
            "error": "PyAutoGUI is not available in the current environment.",
            "target": (x, y),
        }
    
    try:
        pyautogui.moveTo(int(x), int(y), duration=float(duration))
        current_x, current_y = pyautogui.position()
        return {
            "success": True,
            "action": "move_cursor",
            "target": {"x": int(x), "y": int(y)},
            "current_position": {"x": current_x, "y": current_y},
            "message": f"Moved cursor to ({x}, {y})",
        }
    except Exception as e:
        logger.exception(f"Error moving cursor to ({x}, {y}): {e}")
        return {"success": False, "action": "move_cursor", "error": str(e)}


def click_coordinate(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
) -> Dict[str, Any]:
    """
    Safely clicks at the given coordinates or at the current mouse position.
    
    Args:
        x: Optional horizontal pixel coordinate.
        y: Optional vertical pixel coordinate.
        button: Mouse button ('left', 'right', 'middle').
        clicks: Number of clicks (1 for single, 2 for double).
        
    Returns:
        Structured result dict.
    """
    logger.info(f"Clicking: x={x}, y={y}, button={button}, clicks={clicks}")
    if not PYAUTOGUI_AVAILABLE or pyautogui is None:
        return {
            "success": False,
            "action": "click",
            "error": "PyAutoGUI is not available in the current environment.",
        }
    
    try:
        if x is not None and y is not None:
            pyautogui.click(x=int(x), y=int(y), clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
        
        pos = pyautogui.position()
        return {
            "success": True,
            "action": "click",
            "coordinates": {"x": pos.x, "y": pos.y},
            "button": button,
            "clicks": clicks,
            "message": f"Executed {clicks} {button}-click at ({pos.x}, {pos.y})",
        }
    except Exception as e:
        logger.exception(f"Click execution failed: {e}")
        return {"success": False, "action": "click", "error": str(e)}


def type_text(
    text: str,
    interval: float = 0.05,
    press_enter: bool = False,
) -> Dict[str, Any]:
    """
    Safely types text into the active focused window.
    
    Args:
        text: The text string to type.
        interval: Delay between keystrokes in seconds.
        press_enter: Whether to press Enter after typing.
        
    Returns:
        Structured result dict.
    """
    if not text:
        return {"success": False, "action": "type_text", "error": "Empty text string"}
    
    logger.info(f"Typing text: '{text[:20]}...' (length: {len(text)}, enter: {press_enter})")
    
    if PYAUTOGUI_AVAILABLE and pyautogui is not None:
        try:
            pyautogui.write(text, interval=interval)
            if press_enter:
                pyautogui.press("enter")
            return {
                "success": True,
                "action": "type_text",
                "length": len(text),
                "enter_pressed": press_enter,
                "message": f"Successfully typed {len(text)} characters.",
            }
        except Exception as e:
            logger.warning(f"PyAutoGUI typing failed ({e}). Falling back to native system keystrokes...")

    # macOS AppleScript System Events fallback
    if sys.platform == "darwin":
        try:
            escaped = text.replace('\\', '\\\\').replace('"', '\\"')
            script = f'tell application "System Events" to keystroke "{escaped}"'
            if press_enter:
                script += '\ntell application "System Events" to key code 36'
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return {
                "success": True,
                "action": "type_text",
                "method": "macos_applescript",
                "length": len(text),
                "message": f"Successfully injected keystrokes via AppleScript.",
            }
        except Exception as e:
            logger.error(f"AppleScript keystroke failed: {e}")
            return {"success": False, "action": "type_text", "error": str(e)}

    return {
        "success": False,
        "action": "type_text",
        "error": "No input simulation driver available in this environment.",
    }


def press_hotkey(*keys: str) -> Dict[str, Any]:
    """
    Simulates pressing a combination of keyboard keys simultaneously.
    Example: press_hotkey('command', 'space') or press_hotkey('ctrl', 'shift', 'esc')
    """
    if not keys:
        return {"success": False, "action": "hotkey", "error": "No keys specified"}
    
    clean_keys = [str(k).lower().strip() for k in keys]
    logger.info(f"Executing hotkey: {clean_keys}")
    
    if PYAUTOGUI_AVAILABLE and pyautogui is not None:
        try:
            pyautogui.hotkey(*clean_keys)
            return {
                "success": True,
                "action": "hotkey",
                "keys": clean_keys,
                "message": f"Dispatched hotkey: {' + '.join(clean_keys)}",
            }
        except Exception as e:
            logger.error(f"PyAutoGUI hotkey failed: {e}")
            return {"success": False, "action": "hotkey", "error": str(e)}
    
    return {
        "success": False,
        "action": "hotkey",
        "error": "PyAutoGUI is required for hotkey simulation.",
    }


def press_key(key: str) -> Dict[str, Any]:
    """Presses a single keyboard key (e.g., 'enter', 'esc', 'tab', 'space', 'backspace')."""
    clean_key = str(key).lower().strip()
    logger.info(f"Pressing single key: {clean_key}")
    
    if PYAUTOGUI_AVAILABLE and pyautogui is not None:
        try:
            pyautogui.press(clean_key)
            return {"success": True, "action": "press_key", "key": clean_key, "message": f"Pressed key '{clean_key}'"}
        except Exception as e:
            logger.error(f"PyAutoGUI press key failed: {e}")
            return {"success": False, "action": "press_key", "error": str(e)}
    
    return {"success": False, "action": "press_key", "error": "PyAutoGUI is not available"}


def open_application(app_name: str) -> Dict[str, Any]:
    """
    Safely opens or focuses an application on the operating system.
    
    Args:
        app_name: Name of the application (e.g., 'Calculator', 'Google Chrome', 'Notes').
        
    Returns:
        Structured result dict.
    """
    clean_name = app_name.strip()
    logger.info(f"Opening application: {clean_name}")
    
    if sys.platform == "darwin":
        try:
            res = subprocess.run(["open", "-a", clean_name], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return {
                    "success": True,
                    "action": "open_application",
                    "app_name": clean_name,
                    "message": f"Successfully launched '{clean_name}'.",
                }
            return {
                "success": False,
                "action": "open_application",
                "app_name": clean_name,
                "error": res.stderr.strip() or f"Application '{clean_name}' could not be opened.",
            }
        except Exception as e:
            logger.exception(f"Error launching application '{clean_name}': {e}")
            return {"success": False, "action": "open_application", "error": str(e)}
    
    return {
        "success": False,
        "action": "open_application",
        "error": f"Application launching not implemented for platform '{sys.platform}'",
    }


def send_whatsapp_message(
    phone_no: str,
    message: str,
    wait_time: int = 15,
) -> Dict[str, Any]:
    """
    Dispatches a WhatsApp message using pywhatkit or native web URL launcher.
    
    Args:
        phone_no: Recipient phone number with country code (e.g., '+1234567890').
        message: The text message content.
        wait_time: Delay in seconds to wait for WhatsApp Web to load before sending.
        
    Returns:
        Structured result dict.
    """
    clean_phone = phone_no.strip().replace(" ", "").replace("-", "")
    if not clean_phone.startswith("+"):
        clean_phone = f"+{clean_phone}"
    
    logger.info(f"Preparing WhatsApp message to {clean_phone}")
    
    # Strategy 1: pywhatkit instant send
    if PYWHATKIT_AVAILABLE and pywhatkit is not None:
        try:
            # sendwhatmsg_instantly(phone_no, message, wait_time=15, tab_close=True)
            pywhatkit.sendwhatmsg_instantly(clean_phone, message, wait_time=wait_time, tab_close=False)
            return {
                "success": True,
                "action": "send_whatsapp_message",
                "recipient": clean_phone,
                "method": "pywhatkit",
                "message": f"Dispatched WhatsApp message to {clean_phone} via pywhatkit.",
            }
        except Exception as e:
            logger.warning(f"pywhatkit dispatch failed ({e}). Falling back to browser URL scheme...")

    # Strategy 2: Direct browser dispatch to api.whatsapp.com
    import urllib.parse
    encoded_text = urllib.parse.quote(message)
    wa_url = f"https://web.whatsapp.com/send?phone={clean_phone.lstrip('+')}&text={encoded_text}"
    
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", wa_url], check=True, capture_output=True)
            return {
                "success": True,
                "action": "send_whatsapp_message",
                "recipient": clean_phone,
                "method": "browser_url",
                "message": f"Opened WhatsApp chat with pre-filled message for {clean_phone}.",
            }
        except Exception as e:
            return {"success": False, "action": "send_whatsapp_message", "error": str(e)}
    
    return {
        "success": False,
        "action": "send_whatsapp_message",
        "error": "No WhatsApp driver or browser launcher available.",
    }
