"""
Filesystem operations for Ultimate Coding Agent
Secure file and folder management with path validation
"""

import os
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Allowed base directories for security
ALLOWED_BASE_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path("/home/zeds/Desktop/ultimate-agent"),
    Path("/home/zeds/Desktop/ultimate-agent/workspaces"),
    Path("/home/zeds/Desktop/ultimate-agent/data"),
    Path("/home/zeds/Desktop/ultimate-agent/python-agent/data"),
]


@dataclass
class FileOperationResult:
    """Result of a file operation"""
    success: bool
    operation: str
    path: str
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None


class FileManager:
    """Secure file and folder operations"""
    
    def __init__(self):
        self.base_dirs = [Path(d) for d in settings.ALLOWED_COMMANDS.split(",")] if hasattr(settings, 'ALLOWED_COMMANDS') else ALLOWED_BASE_DIRS
        self.workspace_dir = Path("/home/zeds/Desktop/ultimate-agent/workspaces")
        self._ensure_workspace()
    
    def _ensure_workspace(self):
        """Create workspace if not exists"""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> Path:
        """Validate that path is within allowed directories"""
        p = Path(path).expanduser().resolve()
        
        # Check if path is within any allowed base directory
        for base_dir in self.base_dirs:
            try:
                p.relative_to(base_dir)
                return p
            except ValueError:
                continue
        
        # Try workspace directory
        try:
            p.relative_to(self.workspace_dir)
            return p
        except ValueError:
            pass
        
        # Default to workspace
        return self.workspace_dir / Path(path).name
    
    async def create_file(
        self,
        path: str,
        content: str,
        mode: str = "w"
    ) -> FileOperationResult:
        """Create a new file with content"""
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"File created: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="create_file",
                path=str(full_path),
                message=f"✅ File created: {full_path.name}",
                details={"size": len(content), "lines": content.count('\n') + 1}
            )
            
        except Exception as e:
            logger.error(f"Failed to create file: {e}")
            return FileOperationResult(
                success=False,
                operation="create_file",
                path=path,
                message="❌ Failed to create file",
                error=str(e)
            )
    
    async def read_file(self, path: str) -> FileOperationResult:
        """Read file contents"""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="read_file",
                    path=path,
                    message="❌ File not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            logger.info(f"File read: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="read_file",
                path=str(full_path),
                message=f"📄 File read: {full_path.name}",
                details={"size": len(content), "lines": content.count('\n') + 1}
            )
            
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return FileOperationResult(
                success=False,
                operation="read_file",
                path=path,
                message="❌ Failed to read file",
                error=str(e)
            )
    
    async def edit_file(
        self,
        path: str,
        old_text: str = None,
        new_text: str = None,
        append: bool = False,
        prepend: bool = False
    ) -> FileOperationResult:
        """Edit file contents"""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="edit_file",
                    path=path,
                    message="❌ File not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if append:
                new_content = content + new_text
            elif prepend:
                new_content = new_text + content
            elif old_text:
                new_content = content.replace(old_text, new_text, 1)
            else:
                new_content = new_text or content
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            logger.info(f"File edited: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="edit_file",
                path=str(full_path),
                message=f"✏️ File edited: {full_path.name}",
                details={"changes": "appended" if append else "replaced"}
            )
            
        except Exception as e:
            logger.error(f"Failed to edit file: {e}")
            return FileOperationResult(
                success=False,
                operation="edit_file",
                path=path,
                message="❌ Failed to edit file",
                error=str(e)
            )
    
    async def delete_file(self, path: str) -> FileOperationResult:
        """Delete a file"""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="delete_file",
                    path=path,
                    message="❌ File not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            full_path.unlink()
            
            logger.info(f"File deleted: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="delete_file",
                path=str(full_path),
                message=f"🗑️ File deleted: {full_path.name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return FileOperationResult(
                success=False,
                operation="delete_file",
                path=path,
                message="❌ Failed to delete file",
                error=str(e)
            )
    
    async def create_folder(self, path: str) -> FileOperationResult:
        """Create a new folder"""
        try:
            full_path = self._validate_path(path)
            full_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Folder created: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="create_folder",
                path=str(full_path),
                message=f"📁 Folder created: {full_path.name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return FileOperationResult(
                success=False,
                operation="create_folder",
                path=path,
                message="❌ Failed to create folder",
                error=str(e)
            )
    
    async def delete_folder(self, path: str, recursive: bool = False) -> FileOperationResult:
        """Delete a folder"""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="delete_folder",
                    path=path,
                    message="❌ Folder not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            if not full_path.is_dir():
                return FileOperationResult(
                    success=False,
                    operation="delete_folder",
                    path=path,
                    message="❌ Path is not a folder",
                    error=f"Not a directory: {full_path}"
                )
            
            if recursive:
                shutil.rmtree(full_path)
            else:
                full_path.rmdir()
            
            logger.info(f"Folder deleted: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="delete_folder",
                path=str(full_path),
                message=f"🗑️ Folder deleted: {full_path.name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete folder: {e}")
            return FileOperationResult(
                success=False,
                operation="delete_folder",
                path=path,
                message="❌ Failed to delete folder",
                error=str(e)
            )
    
    async def list_directory(self, path: str = ".") -> FileOperationResult:
        """List directory contents"""
        try:
            if path == ".":
                full_path = self.workspace_dir
            else:
                full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="list_directory",
                    path=path,
                    message="❌ Path not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            if not full_path.is_dir():
                return FileOperationResult(
                    success=False,
                    operation="list_directory",
                    path=path,
                    message="❌ Path is not a directory",
                    error=f"Not a directory: {full_path}"
                )
            
            items = []
            for item in sorted(full_path.iterdir()):
                item_type = "📁" if item.is_dir() else "📄"
                items.append(f"{item_type} {item.name}")
            
            if not items:
                items = ["(empty)"]
            
            logger.info(f"Listed directory: {full_path}")
            
            return FileOperationResult(
                success=True,
                operation="list_directory",
                path=str(full_path),
                message=f"📂 {full_path.name}:\n" + "\n".join(items),
                details={"count": len(items)}
            )
            
        except Exception as e:
            logger.error(f"Failed to list directory: {e}")
            return FileOperationResult(
                success=False,
                operation="list_directory",
                path=path,
                message="❌ Failed to list directory",
                error=str(e)
            )
    
    async def get_file_info(self, path: str) -> FileOperationResult:
        """Get file/folder information"""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return FileOperationResult(
                    success=False,
                    operation="get_file_info",
                    path=path,
                    message="❌ Path not found",
                    error=f"Path does not exist: {full_path}"
                )
            
            stat = full_path.stat()
            info = {
                "name": full_path.name,
                "type": "directory" if full_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
            
            return FileOperationResult(
                success=True,
                operation="get_file_info",
                path=str(full_path),
                message=f"📋 {full_path.name}: {info['type']} ({info['size']} bytes)",
                details=info
            )
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return FileOperationResult(
                success=False,
                operation="get_file_info",
                path=path,
                message="❌ Failed to get file info",
                error=str(e)
            )
    
    async def copy_file(self, source: str, destination: str) -> FileOperationResult:
        """Copy a file"""
        try:
            src = self._validate_path(source)
            dst = self._validate_path(destination)
            
            if not src.exists():
                return FileOperationResult(
                    success=False,
                    operation="copy_file",
                    path=source,
                    message="❌ Source file not found",
                    error=f"Source does not exist: {src}"
                )
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            
            logger.info(f"File copied: {src} -> {dst}")
            
            return FileOperationResult(
                success=True,
                operation="copy_file",
                path=destination,
                message=f"📋 File copied to: {dst.name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return FileOperationResult(
                success=False,
                operation="copy_file",
                path=source,
                message="❌ Failed to copy file",
                error=str(e)
            )
    
    async def move_file(self, source: str, destination: str) -> FileOperationResult:
        """Move/rename a file"""
        try:
            src = self._validate_path(source)
            dst = self._validate_path(destination)
            
            if not src.exists():
                return FileOperationResult(
                    success=False,
                    operation="move_file",
                    path=source,
                    message="❌ Source file not found",
                    error=f"Source does not exist: {src}"
                )
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            
            logger.info(f"File moved: {src} -> {dst}")
            
            return FileOperationResult(
                success=True,
                operation="move_file",
                path=destination,
                message=f"📦 File moved to: {dst.name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return FileOperationResult(
                success=False,
                operation="move_file",
                path=source,
                message="❌ Failed to move file",
                error=str(e)
            )


# Global file manager
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """Get or create file manager"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
