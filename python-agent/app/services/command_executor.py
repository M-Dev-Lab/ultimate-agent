"""
Secure command execution with sandboxing
Prevents command injection and unauthorized execution
"""

import subprocess
import shlex
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from app.core.config import settings
from app.security.validators import SecurityValidator

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command execution"""
    returncode: int
    stdout: str
    stderr: str
    success: bool

    def to_dict(self) -> dict:
        return {
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "success": self.success,
        }


class SecureCommandExecutor:
    """
    Safely executes commands with security restrictions
    Prevents command injection, shell escapes, and unauthorized operations
    """

    # Whitelist of allowed commands
    ALLOWED_COMMANDS = set(settings.allowed_commands)

    # Environment variables to filter out (security-sensitive)
    RESTRICTED_ENV_VARS = set(settings.restricted_env_vars)

    # Maximum execution timeout in seconds
    MAX_TIMEOUT = 300

    @classmethod
    def validate_command(cls, command: str) -> Tuple[str, bool]:
        """
        Validate command before execution
        Returns (command, is_valid) tuple
        """
        try:
            # Parse command using shlex
            args = shlex.split(command)

            if not args:
                return command, False

            # Check if first element (command name) is in whitelist
            if args[0] not in cls.ALLOWED_COMMANDS:
                logger.warning(f"Command not whitelisted: {args[0]}")
                return command, False

            # Validate each argument for injection attempts
            for arg in args[1:]:
                SecurityValidator.sanitize_shell_input(arg)

            return command, True
        except ValueError as e:
            logger.warning(f"Command validation failed: {e}")
            return command, False

    @classmethod
    def _create_safe_env(cls) -> Dict[str, str]:
        """
        Create a sanitized environment for subprocess
        Removes sensitive environment variables
        """
        safe_env = os.environ.copy()

        # Remove sensitive variables
        for var in cls.RESTRICTED_ENV_VARS:
            safe_env.pop(var, None)

        # Restrict PATH to known safe locations
        safe_env["PATH"] = "/usr/local/bin:/usr/bin:/bin"

        # Disable shell history
        safe_env["HISTFILE"] = "/dev/null"

        return safe_env

    @classmethod
    def execute(
        cls,
        command: str,
        cwd: Optional[Path] = None,
        timeout: int = 30,
        capture_output: bool = True,
    ) -> CommandResult:
        """
        Execute a command securely

        Args:
            command: Command string to execute
            cwd: Working directory for execution
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            CommandResult with execution details

        Raises:
            ValueError: If command validation fails
            subprocess.TimeoutExpired: If execution exceeds timeout
        """
        # Validate command
        _, is_valid = cls.validate_command(command)
        if not is_valid:
            raise ValueError(f"Invalid command: {command}")

        # Validate working directory if provided
        if cwd:
            try:
                cwd = SecurityValidator.sanitize_path(cwd, base_dir=Path(settings.workspace_dir))
                # Create directory if it doesn't exist
                cwd.mkdir(parents=True, exist_ok=True)
            except ValueError as e:
                raise ValueError(f"Invalid working directory: {e}")

        # Enforce timeout limits
        timeout = min(timeout, cls.MAX_TIMEOUT)

        try:
            # Parse command into arguments
            args = shlex.split(command)

            logger.info(f"Executing command: {args[0]} (in {cwd})")

            # Execute command
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=capture_output,
                timeout=timeout,
                env=cls._create_safe_env(),
                text=True,
                check=False,  # Don't raise on non-zero exit
            )

            success = result.returncode == 0

            logger.info(
                f"Command completed: {args[0]} - "
                f"returncode={result.returncode}, success={success}"
            )

            return CommandResult(
                returncode=result.returncode,
                stdout=result.stdout[:10000] if result.stdout else "",  # Limit output
                stderr=result.stderr[:10000] if result.stderr else "",
                success=success,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            raise ValueError(f"Command execution exceeded timeout of {timeout}s")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise ValueError(f"Command execution failed: {str(e)}")

    @classmethod
    def execute_git_command(
        cls,
        git_command: str,
        repo_path: Path,
        timeout: int = 60,
    ) -> CommandResult:
        """
        Execute a git command with extra validation
        """
        # Validate repository path
        try:
            repo_path = SecurityValidator.sanitize_path(
                str(repo_path), base_dir=Path(settings.workspace_dir)
            )
        except ValueError as e:
            raise ValueError(f"Invalid repository path: {e}")

        # Validate git command
        git_args = shlex.split(git_command)
        if git_args[0] != "git":
            raise ValueError("Only git commands are allowed")

        # Dangerous git commands
        dangerous_commands = ["rm", "force-push", "reset --hard", "clean -fd"]
        command_str = " ".join(git_args).lower()
        for dangerous in dangerous_commands:
            if dangerous in command_str:
                raise ValueError(f"Dangerous git command: {dangerous}")

        full_command = f"git {git_command}"
        return cls.execute(full_command, cwd=repo_path, timeout=timeout)

    @classmethod
    def execute_npm_command(
        cls,
        npm_command: str,
        project_path: Path,
        timeout: int = 120,
    ) -> CommandResult:
        """
        Execute an npm command safely
        """
        # Validate project path
        try:
            project_path = SecurityValidator.sanitize_path(
                str(project_path), base_dir=Path(settings.workspace_dir)
            )
        except ValueError as e:
            raise ValueError(f"Invalid project path: {e}")

        # Allow only safe npm commands
        allowed_npm_commands = ["install", "run", "test", "build"]
        npm_args = shlex.split(npm_command)

        if npm_args[0] != "npm":
            raise ValueError("Only npm commands are allowed")

        if not any(cmd in npm_command for cmd in allowed_npm_commands):
            raise ValueError(f"npm command not allowed: {npm_command}")

        return cls.execute(npm_command, cwd=project_path, timeout=timeout)
