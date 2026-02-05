"""
Advanced Workflow Logger for Ultimate Coding Agent
Provides detailed, color-coded, and timestamped logs for terminal visibility.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

class WorkflowLogger:
    # ANSI Color Codes
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

    @staticmethod
    def _get_timestamp() -> str:
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    @classmethod
    def log_step(cls, workflow_name: str, step_name: str, details: str = "", data: Optional[Dict] = None):
        """Log a specific step in a workflow"""
        ts = cls._get_timestamp()
        header = f"{cls.MAGENTA}{cls.BOLD}[WORKFLOW STEP]{cls.RESET}"
        name_tag = f"{cls.CYAN}{workflow_name.upper()}{cls.RESET}"
        step_tag = f"{cls.YELLOW}{step_name}{cls.RESET}"
        
        print(f"\n{header} {cls.BLUE}{ts}{cls.RESET} | {name_tag} -> {step_tag}")
        if details:
            print(f"               ℹ️  {details}")
        if data:
            for k, v in data.items():
                print(f"               📦 {cls.GREEN}{k}{cls.RESET}: {v}")

    @classmethod
    def log_transition(cls, from_state: str, to_state: str, trigger: str = ""):
        """Log a state machine transition"""
        ts = cls._get_timestamp()
        header = f"{cls.BLUE}{cls.BOLD}[STATE TRANSITION]{cls.RESET}"
        trigger_str = f" via {cls.YELLOW}'{trigger}'{cls.RESET}" if trigger else ""
        
        print(f"{header} {cls.BLUE}{ts}{cls.RESET} | {cls.RED}{from_state}{cls.RESET} ➔ {cls.GREEN}{to_state}{cls.RESET}{trigger_str}")

    @classmethod
    def log_ai_action(cls, operation: str, prompt: str, token_count: Optional[int] = None):
        """Log AI generation calls"""
        ts = cls._get_timestamp()
        header = f"{cls.MAGENTA}{cls.BOLD}[AI BRAIN]{cls.RESET}"
        op_tag = f"{cls.YELLOW}{operation}{cls.RESET}"
        
        preview = prompt[:100].replace("\n", " ") + "..." if len(prompt) > 100 else prompt
        print(f"{header} {cls.BLUE}{ts}{cls.RESET} | {op_tag}")
        print(f"               🧠 Prompt: {cls.BLUE}{preview}{cls.RESET}")
        if token_count:
            print(f"               📊 Tokens: {token_count}")

    @classmethod
    def log_success(cls, message: str):
        """Log a successful operation"""
        ts = cls._get_timestamp()
        header = f"{cls.GREEN}{cls.BOLD}[SUCCESS]{cls.RESET}"
        print(f"{header} {cls.BLUE}{ts}{cls.RESET} | {message}")

    @classmethod
    def log_error(cls, message: str, error: Optional[Exception] = None):
        """Log an error"""
        ts = cls._get_timestamp()
        header = f"{cls.RED}{cls.BOLD}[ERROR]{cls.RESET}"
        print(f"{header} {cls.BLUE}{ts}{cls.RESET} | {cls.BOLD}{message}{cls.RESET}")
        if error:
            print(f"               ❌ {cls.RED}{str(error)}{cls.RESET}")

    @classmethod
    def log_system(cls, message: str):
        """Log a system message"""
        ts = cls._get_timestamp()
        header = f"{cls.MAGENTA}{cls.BOLD}[SYSTEM]{cls.RESET}"
        print(f"{header} {cls.BLUE}{ts}{cls.RESET} | {message}")
