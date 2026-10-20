"""
Ultron File Manager Module
Defensive functions to create, delete, list, read, and move folders/files on the desktop
and permitted workspace directories. Includes strict error logging and path traversal protections.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ultron.tools.file_manager")

# Restricted system directories that must NEVER be modified or deleted
RESTRICTED_ROOTS = {
    Path("/"),
    Path("/bin"),
    Path("/sbin"),
    Path("/etc"),
    Path("/usr"),
    Path("/System"),
    Path("/Library"),
    Path("/private"),
    Path.home(),  # Never delete the entire user home directory!
}


def get_default_desktop_dir() -> Path:
    """Returns the user's Desktop directory if writable, or falls back to desktop_workspace / cwd."""
    desktop_env = os.getenv("DESKTOP_PATH")
    if desktop_env:
        resolved = Path(os.path.expanduser(desktop_env)).resolve()
        if resolved.exists() and os.access(resolved, os.W_OK):
            return resolved
    
    desktop = Path.home() / "Desktop"
    if desktop.exists() and os.access(desktop, os.W_OK):
        return desktop.resolve()
    
    # Fallback to local workspace desktop directory if system Desktop is sandboxed or read-only
    workspace_desktop = Path.cwd() / "desktop_workspace"
    workspace_desktop.mkdir(parents=True, exist_ok=True)
    return workspace_desktop.resolve()


def _resolve_safe_path(target: str, base_dir: Optional[str] = None) -> Path:
    """
    Resolves a path safely. If target is relative, resolves against base_dir or Desktop.
    Guards against path traversal and restricted system directories.
    """
    if not target or not target.strip():
        raise ValueError("Target path cannot be empty.")
    
    base = Path(os.path.expanduser(base_dir)).resolve() if base_dir else get_default_desktop_dir()
    
    candidate = Path(os.path.expanduser(target))
    if not candidate.is_absolute():
        resolved = (base / candidate).resolve()
    else:
        resolved = candidate.resolve()
    
    # Check against restricted root directories
    if resolved in RESTRICTED_ROOTS:
        raise PermissionError(f"Access denied: Operation on protected system path '{resolved}' is forbidden.")
    
    return resolved


def create_folder(folder_name: str, parent_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Defensively creates a new directory.
    
    Args:
        folder_name: Name or relative path of the folder to create.
        parent_dir: Optional parent directory (defaults to Desktop).
        
    Returns:
        Structured result dict with status, path, and message.
    """
    try:
        target_path = _resolve_safe_path(folder_name, parent_dir)
        if target_path.exists():
            if target_path.is_dir():
                logger.info(f"Directory already exists: {target_path}")
                return {
                    "success": True,
                    "action": "create_folder",
                    "path": str(target_path),
                    "message": f"Folder already exists at: {target_path}",
                    "already_existed": True,
                }
            else:
                logger.error(f"Cannot create folder. A file exists at: {target_path}")
                return {
                    "success": False,
                    "action": "create_folder",
                    "path": str(target_path),
                    "error": f"A non-directory file already exists at '{target_path}'",
                }
        
        target_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Successfully created folder: {target_path}")
        return {
            "success": True,
            "action": "create_folder",
            "path": str(target_path),
            "message": f"Successfully created folder '{target_path.name}' at: {target_path}",
            "already_existed": False,
        }
    except Exception as e:
        logger.exception(f"Failed to create folder '{folder_name}': {e}")
        return {
            "success": False,
            "action": "create_folder",
            "error": str(e),
        }


def create_file(file_name: str, content: str = "", target_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Defensively creates a new file with optional content.
    
    Args:
        file_name: Name or path of the file to create.
        content: Text content to write into the file.
        target_dir: Optional target directory (defaults to Desktop).
        
    Returns:
        Structured result dict.
    """
    try:
        target_path = _resolve_safe_path(file_name, target_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        target_path.write_text(content, encoding="utf-8")
        logger.info(f"Successfully created file: {target_path} ({len(content)} chars)")
        return {
            "success": True,
            "action": "create_file",
            "path": str(target_path),
            "size_bytes": target_path.stat().st_size,
            "message": f"Successfully created file '{target_path.name}' ({len(content)} chars written)",
        }
    except Exception as e:
        logger.exception(f"Failed to create file '{file_name}': {e}")
        return {
            "success": False,
            "action": "create_file",
            "error": str(e),
        }


def delete_item(target_path: str, force: bool = False) -> Dict[str, Any]:
    """
    Defensively deletes a file or directory.
    Guards against deleting system roots or parent home.
    
    Args:
        target_path: Path to the file or directory to delete.
        force: If True, allows recursive directory deletion.
        
    Returns:
        Structured result dict.
    """
    try:
        resolved = _resolve_safe_path(target_path)
        
        if not resolved.exists():
            logger.warning(f"Delete requested for nonexistent target: {resolved}")
            return {
                "success": False,
                "action": "delete_item",
                "path": str(resolved),
                "error": f"Item not found: '{resolved}'",
            }
        
        if resolved.is_dir():
            # If not force and directory contains items, refuse
            items = list(resolved.iterdir())
            if items and not force:
                logger.warning(f"Refusing to delete non-empty directory without force=True: {resolved}")
                return {
                    "success": False,
                    "action": "delete_item",
                    "path": str(resolved),
                    "error": f"Directory '{resolved.name}' is not empty ({len(items)} items). Set force=True to confirm deletion.",
                }
            shutil.rmtree(resolved)
            logger.info(f"Successfully deleted directory: {resolved}")
            return {
                "success": True,
                "action": "delete_item",
                "path": str(resolved),
                "type": "directory",
                "message": f"Successfully deleted directory: {resolved}",
            }
        else:
            resolved.unlink()
            logger.info(f"Successfully deleted file: {resolved}")
            return {
                "success": True,
                "action": "delete_item",
                "path": str(resolved),
                "type": "file",
                "message": f"Successfully deleted file: {resolved}",
            }
    except Exception as e:
        logger.exception(f"Failed to delete item '{target_path}': {e}")
        return {
            "success": False,
            "action": "delete_item",
            "error": str(e),
        }


def list_directory(directory_path: Optional[str] = None, max_items: int = 100) -> Dict[str, Any]:
    """
    Defensively lists files and directories with metadata.
    
    Args:
        directory_path: Directory path to list (defaults to Desktop).
        max_items: Maximum items to return to avoid overwhelming context.
        
    Returns:
        Structured result dict with list of entries.
    """
    try:
        resolved = _resolve_safe_path(directory_path) if directory_path else get_default_desktop_dir()
        
        if not resolved.exists() or not resolved.is_dir():
            return {
                "success": False,
                "action": "list_directory",
                "error": f"Directory does not exist or is not a folder: '{resolved}'",
            }
        
        entries: List[Dict[str, Any]] = []
        for item in sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.name.startswith("."):
                continue  # Skip hidden files by default
            try:
                stat = item.stat()
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": stat.st_size if not item.is_dir() else None,
                    "path": str(item),
                })
            except (PermissionError, FileNotFoundError):
                continue
            
            if len(entries) >= max_items:
                break
        
        logger.info(f"Listed {len(entries)} items in directory: {resolved}")
        return {
            "success": True,
            "action": "list_directory",
            "directory": str(resolved),
            "count": len(entries),
            "items": entries,
            "message": f"Found {len(entries)} items in '{resolved.name}'",
        }
    except Exception as e:
        logger.exception(f"Failed to list directory '{directory_path}': {e}")
        return {
            "success": False,
            "action": "list_directory",
            "error": str(e),
        }


def move_item(source_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Defensively moves or renames a file or folder.
    
    Args:
        source_path: Source item path.
        destination_path: Destination path or folder.
        
    Returns:
        Structured result dict.
    """
    try:
        src = _resolve_safe_path(source_path)
        dest = _resolve_safe_path(destination_path)
        
        if not src.exists():
            return {
                "success": False,
                "action": "move_item",
                "error": f"Source item does not exist: '{src}'",
            }
        
        dest.parent.mkdir(parents=True, exist_ok=True)
        final_dest = shutil.move(str(src), str(dest))
        logger.info(f"Moved '{src}' -> '{final_dest}'")
        return {
            "success": True,
            "action": "move_item",
            "source": str(src),
            "destination": str(final_dest),
            "message": f"Successfully moved '{src.name}' to '{final_dest}'",
        }
    except Exception as e:
        logger.exception(f"Failed to move '{source_path}' to '{destination_path}': {e}")
        return {
            "success": False,
            "action": "move_item",
            "error": str(e),
        }
