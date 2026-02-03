"""
Security utilities for input validation and sanitization
Prevents injection attacks and malicious input
"""

import re
import html
from typing import Any, List
from pathlib import Path


class SecurityValidator:
    """Centralized security validation"""

    # Regex patterns for dangerous inputs
    SHELL_INJECTION_PATTERN = re.compile(r'[;&|`$\\()><\n\r]')
    SQL_INJECTION_PATTERN = re.compile(r"('|(--)|;|/\*|\*/|xp_|sp_)", re.IGNORECASE)
    PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.(/|\\)|\.\.%2[fF]')
    DANGEROUS_FILE_EXTENSIONS = {'.exe', '.bat', '.sh', '.cmd', '.com', '.scr'}

    @staticmethod
    def sanitize_shell_input(value: str) -> str:
        """
        Sanitize shell command input
        Raises ValueError if dangerous patterns detected
        """
        if not isinstance(value, str):
            raise ValueError("Input must be string")

        if len(value) > 1000:
            raise ValueError("Input exceeds maximum length")

        # Check for shell injection patterns
        if SecurityValidator.SHELL_INJECTION_PATTERN.search(value):
            raise ValueError("Input contains invalid shell characters")

        # Check for common shell commands
        dangerous_commands = [
            'rm -rf', 'dd if=', ':/dev/', 'chmod', 'wget', 'curl',
            'nc', 'bash', 'sh', 'exec', 'fork', 'bomb'
        ]
        
        value_lower = value.lower()
        for cmd in dangerous_commands:
            if cmd in value_lower:
                raise ValueError(f"Command not allowed: {cmd}")

        return value

    @staticmethod
    def sanitize_path(path: str, base_dir: Path = None) -> Path:
        """
        Validate and sanitize file paths
        Prevents path traversal attacks
        """
        if not isinstance(path, str):
            raise ValueError("Path must be string")

        # Check for path traversal
        if SecurityValidator.PATH_TRAVERSAL_PATTERN.search(path):
            raise ValueError("Path traversal attempt detected")

        # Normalize path
        normalized = Path(path).resolve()

        # If base_dir provided, ensure normalized path is within it
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                normalized.relative_to(base_dir)
            except ValueError:
                raise ValueError(f"Path is outside allowed directory: {base_dir}")

        # Check for symlinks
        if normalized.is_symlink():
            raise ValueError("Symlinks are not allowed for security reasons")

        return normalized

    @staticmethod
    def sanitize_project_name(name: str) -> str:
        """
        Validate project name
        Only alphanumeric, hyphens, underscores allowed
        """
        if not isinstance(name, str):
            raise ValueError("Project name must be string")

        if not re.match(r'^[a-zA-Z0-9_-]{1,50}$', name):
            raise ValueError(
                "Project name must contain only alphanumeric characters, hyphens, underscores (1-50 chars)"
            )

        return name

    @staticmethod
    def sanitize_goal(goal: str) -> str:
        """
        Sanitize goal input for code generation
        Removes dangerous patterns but preserves readability
        """
        if not isinstance(goal, str):
            raise ValueError("Goal must be string")

        if len(goal) < 5:
            raise ValueError("Goal must be at least 5 characters")

        if len(goal) > 2000:
            raise ValueError("Goal exceeds maximum length of 2000 characters")

        # Remove leading/trailing whitespace
        goal = goal.strip()

        # Escape HTML to prevent XSS if used in web interface
        goal = html.escape(goal)

        # Check for SQL injection patterns (in case goal is logged to database)
        if SecurityValidator.SQL_INJECTION_PATTERN.search(goal):
            raise ValueError("Goal contains suspicious SQL patterns")

        return goal

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        return email

    @staticmethod
    def validate_url(url: str, allowed_domains: List[str] = None) -> str:
        """
        Validate URL format
        Optionally restrict to allowed domains (SSRF prevention)
        """
        # Basic URL pattern
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if not re.match(pattern, url):
            raise ValueError("Invalid URL format")

        # Check against allowed domains if provided
        if allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain not in allowed_domains:
                raise ValueError(f"Domain not allowed: {domain}")

        return url

    @staticmethod
    def sanitize_json_keys(obj: Any) -> Any:
        """
        Recursively sanitize JSON object keys
        Removes keys with dangerous patterns
        """
        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():
                # Remove keys that look like they're trying SQL injection
                if SecurityValidator.SQL_INJECTION_PATTERN.search(str(key)):
                    continue
                sanitized[key] = SecurityValidator.sanitize_json_keys(value)
            return sanitized
        elif isinstance(obj, list):
            return [SecurityValidator.sanitize_json_keys(item) for item in obj]
        else:
            return obj

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> str:
        """Validate file extension"""
        path = Path(filename)
        if path.suffix.lower() not in allowed_extensions:
            raise ValueError(
                f"File extension {path.suffix} not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        if path.suffix.lower() in SecurityValidator.DANGEROUS_FILE_EXTENSIONS:
            raise ValueError(f"File extension {path.suffix} is not allowed for security reasons")
        return filename


class RateLimiter:
    """Simple in-memory rate limiter for demonstration"""
    
    def __init__(self):
        from collections import defaultdict
        from time import time
        self.requests = defaultdict(list)
        self.time = time

    def is_allowed(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Check if request is allowed based on rate limit"""
        now = self.time()
        cutoff = now - window_seconds

        # Remove old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff]

        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Add new request
        self.requests[key].append(now)
        return True
