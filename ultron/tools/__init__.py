"""
Ultron Tools Package
Exports file management, computer vision, and desktop automation tools.
Provides centralized tool dispatch and tool metadata definitions for the AI brain.
"""

from typing import Dict, Any, Callable

from . import file_manager
from . import vision
from . import automation

# Tool Dispatch Table: maps string tool names to Python callables
TOOL_DISPATCH: Dict[str, Callable[..., Dict[str, Any]]] = {
    # File Management
    "file_manager.create_folder": file_manager.create_folder,
    "file_manager.create_file": file_manager.create_file,
    "file_manager.delete_item": file_manager.delete_item,
    "file_manager.list_directory": file_manager.list_directory,
    "file_manager.move_item": file_manager.move_item,

    # Vision & Screen Capture
    "vision.capture_screenshot": vision.capture_screenshot,
    "vision.get_latest_screenshot": vision.get_latest_screenshot,

    # Desktop Automation & Messaging
    "automation.click_coordinate": automation.click_coordinate,
    "automation.move_cursor": automation.move_cursor,
    "automation.type_text": automation.type_text,
    "automation.press_hotkey": automation.press_hotkey,
    "automation.press_key": automation.press_key,
    "automation.open_application": automation.open_application,
    "automation.send_whatsapp_message": automation.send_whatsapp_message,
    "automation.get_screen_geometry": automation.get_screen_geometry,
}

# Declarative tool specifications for the LLM system prompt
TOOL_CATALOG = [
    {
        "name": "file_manager.create_folder",
        "description": "Create a new directory on the Desktop or specified path.",
        "parameters": {
            "folder_name": {"type": "string", "required": True, "description": "Name or relative path of the folder to create"},
            "parent_dir": {"type": "string", "required": False, "description": "Optional parent directory (defaults to Desktop)"}
        }
    },
    {
        "name": "file_manager.create_file",
        "description": "Create a new file on the Desktop or specified path with optional text content.",
        "parameters": {
            "file_name": {"type": "string", "required": True, "description": "Name of the file to create"},
            "content": {"type": "string", "required": False, "description": "Text content to write into the file"},
            "target_dir": {"type": "string", "required": False, "description": "Optional directory (defaults to Desktop)"}
        }
    },
    {
        "name": "file_manager.delete_item",
        "description": "Defensively delete a file or directory from the desktop/workspace.",
        "parameters": {
            "target_path": {"type": "string", "required": True, "description": "Path or name of item to delete"},
            "force": {"type": "boolean", "required": False, "description": "Set True to delete non-empty folders"}
        }
    },
    {
        "name": "file_manager.list_directory",
        "description": "List files and folders in a directory (defaults to Desktop).",
        "parameters": {
            "directory_path": {"type": "string", "required": False, "description": "Path to list (defaults to Desktop)"},
            "max_items": {"type": "integer", "required": False, "description": "Max entries to return"}
        }
    },
    {
        "name": "file_manager.move_item",
        "description": "Move or rename a file or folder from source to destination.",
        "parameters": {
            "source_path": {"type": "string", "required": True, "description": "Source file or directory path"},
            "destination_path": {"type": "string", "required": True, "description": "Destination path or new name"}
        }
    },
    {
        "name": "vision.capture_screenshot",
        "description": "Capture a stamped screenshot of the entire desktop and save to screenshots directory.",
        "parameters": {
            "prefix": {"type": "string", "required": False, "description": "Filename prefix (default: screenshot)"}
        }
    },
    {
        "name": "vision.get_latest_screenshot",
        "description": "Retrieve metadata and path of the most recent screenshot.",
        "parameters": {}
    },
    {
        "name": "automation.click_coordinate",
        "description": "Simulate clicking the mouse at specific screen coordinates or current position.",
        "parameters": {
            "x": {"type": "integer", "required": False, "description": "X coordinate in pixels"},
            "y": {"type": "integer", "required": False, "description": "Y coordinate in pixels"},
            "button": {"type": "string", "required": False, "description": "Mouse button: 'left', 'right', 'middle'"},
            "clicks": {"type": "integer", "required": False, "description": "Number of clicks (1 or 2)"}
        }
    },
    {
        "name": "automation.move_cursor",
        "description": "Smoothly move the mouse cursor to a specific coordinate.",
        "parameters": {
            "x": {"type": "integer", "required": True, "description": "Target X pixel coordinate"},
            "y": {"type": "integer", "required": True, "description": "Target Y pixel coordinate"},
            "duration": {"type": "number", "required": False, "description": "Duration of animation in seconds (default: 0.2)"}
        }
    },
    {
        "name": "automation.type_text",
        "description": "Type text into the currently active/focused window.",
        "parameters": {
            "text": {"type": "string", "required": True, "description": "Text to type"},
            "press_enter": {"type": "boolean", "required": False, "description": "Press Enter key after typing"}
        }
    },
    {
        "name": "automation.press_hotkey",
        "description": "Trigger a keyboard hotkey combination like command+space or ctrl+c.",
        "parameters": {
            "keys": {"type": "array", "required": True, "description": "List of key names e.g. ['command', 'space'] or ['ctrl', 'c']"}
        }
    },
    {
        "name": "automation.press_key",
        "description": "Press a single keyboard key (e.g. 'enter', 'esc', 'tab', 'space').",
        "parameters": {
            "key": {"type": "string", "required": True, "description": "Key name"}
        }
    },
    {
        "name": "automation.open_application",
        "description": "Launch or focus an application (e.g. 'Calculator', 'Notes', 'Google Chrome').",
        "parameters": {
            "app_name": {"type": "string", "required": True, "description": "Name of the app to launch"}
        }
    },
    {
        "name": "automation.send_whatsapp_message",
        "description": "Send a WhatsApp message to a phone number using pywhatkit or web URL.",
        "parameters": {
            "phone_no": {"type": "string", "required": True, "description": "Phone number with country code, e.g. '+1234567890'"},
            "message": {"type": "string", "required": True, "description": "Message content"}
        }
    },
    {
        "name": "none",
        "description": "Use when the user prompt is a general conversational question, greeting, or does not require a desktop action.",
        "parameters": {}
    }
]
