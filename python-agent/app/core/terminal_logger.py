
"""
Terminal Logger for Ultimate Agent
Provides high-visibility terminal output for background operations
"""

import sys

# ANSI Color Codes
CLR_RED = "\033[0;31m"
CLR_GREEN = "\033[0;32m"
CLR_YELLOW = "\033[1;33m"
CLR_BLUE = "\033[0;34m"
CLR_MAGENTA = "\033[0;35m"
CLR_CYAN = "\033[0;36m"
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

class TerminalActionLogger:
    @staticmethod
    def log_action(action_name: str, details: str = "", success: bool = True):
        color = CLR_GREEN if success else CLR_RED
        symbol = "✅" if success else "❌"
        print(f"\n{CLR_BOLD}{CLR_CYAN}[ACTION]{CLR_RESET} {color}{symbol} {CLR_BOLD}{action_name.upper()}{CLR_RESET}")
        if details:
            print(f"         {CLR_YELLOW}ℹ️  {details}{CLR_RESET}")
        sys.stdout.flush()

    @staticmethod
    def log_workflow(user_id: int, state: str, message: str):
        print(f"\n{CLR_BOLD}{CLR_MAGENTA}[WORKFLOW]{CLR_RESET} {CLR_BOLD}User: {user_id}{CLR_RESET}")
        print(f"           {CLR_CYAN}📍 State: {state}{CLR_RESET}")
        print(f"           {CLR_YELLOW}✉️  Msg:   {message[:50]}...{CLR_RESET}")
        sys.stdout.flush()

    @staticmethod
    def log_skill(skill_name: str, user_id: int):
        print(f"\n{CLR_BOLD}{CLR_BLUE}[SKILL]{CLR_RESET} {CLR_BOLD}Executing: {skill_name}{CLR_RESET}")
        print(f"        {CLR_CYAN}👤 User: {user_id}{CLR_RESET}")
        sys.stdout.flush()

    @staticmethod
    def log_system(msg: str):
        print(f"\n{CLR_BOLD}{CLR_YELLOW}[SYSTEM]{CLR_RESET} {CLR_BOLD}{msg}{CLR_RESET}")
        sys.stdout.flush()
