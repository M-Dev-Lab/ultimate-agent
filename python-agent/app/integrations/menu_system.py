"""
Unified Menu System for Telegram Bot
Consolidates all menu navigation, smart responses, and command handlers
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

@dataclass
class MenuButton:
    """Menu button configuration"""
    id: str
    emoji: str
    label: str
    description: str
    callback_data: str

@dataclass
class MenuConfig:
    """Menu submenu configuration"""
    id: str
    title: str
    parent: str
    buttons: List[MenuButton]

class SmartResponseHooks:
    """Smart response templates for different actions"""
    
    HOOKS = {
        'build': {
            'success': [
                "🦞 Built it!",
                "⚡ Done and done!",
                "🔥 That was quick!",
                "✅ Project ready!",
                "🚀 Built and ready to ship!"
            ],
            'failure': [
                "🤔 Hit a snag...",
                "⚠️ Hold up, found an issue...",
                "🔧 Need to fix something first...",
                "❌ Build failed, let me explain..."
            ]
        },
        'deploy': {
            'success': [
                "🚀 Deployed!",
                "✅ Live now!",
                "🌍 It's out there!",
                "📡 Pushed to production!",
                "🎯 Deploy successful!"
            ],
            'failure': [
                "⚠️ Deploy failed...",
                "🔧 Deployment issue detected...",
                "❌ Couldn't deploy, here's why...",
                "🚫 Production deployment blocked..."
            ]
        },
        'post': {
            'success': [
                "📱 Posted!",
                "✅ It's live!",
                "🎯 Shared across platforms!",
                "📡 Post published!",
                "🔥 Content is out!"
            ],
            'failure': [
                "⚠️ Couldn't post...",
                "🔧 Posting failed...",
                "❌ Social media error...",
                "🚫 Post blocked..."
            ]
        },
        'fix': {
            'success': [
                "🔧 Fixed!",
                "✅ Bug squashed!",
                "🐛 Issue resolved!",
                "⚡ All good now!",
                "🎯 Fixed and tested!"
            ],
            'failure': [
                "🤔 Still debugging...",
                "⚠️ Fix didn't work...",
                "🔍 Need more investigation...",
                "❌ Issue persists..."
            ]
        },
        'test': {
            'success': [
                "🧪 All tests passed!",
                "✅ Green across the board!",
                "🎯 100% success rate!",
                "⚡ Tests complete!",
                "🔥 Everything works!"
            ],
            'failure': [
                "⚠️ Some tests failed...",
                "🔍 Found failing test...",
                "❌ Test suite failed...",
                "🚫 Coverage issue detected..."
            ]
        },
        'code': {
            'success': [
                "✨ Code generated!",
                "🎯 Ready to use!",
                "⚡ Here's your code!",
                "🔥 Code snippet ready!",
                "✅ Code complete!"
            ],
            'failure': [
                "🤔 Code generation failed...",
                "⚠️ Couldn't generate code...",
                "🔧 Error in code generation...",
                "❌ Code generation issue..."
            ]
        }
    }
    
    @classmethod
    def get_response(cls, action: str, success: bool) -> str:
        """Get a smart response for an action"""
        import random
        action_hooks = cls.HOOKS.get(action, {})
        status_key = 'success' if success else 'failure'
        responses = action_hooks.get(status_key, ["✅ Done!" if success else "⚠️ Error"])
        return random.choice(responses)


class MenuManager:
    """Menu management system for Telegram bot"""
    
    MAIN_MENU_BUTTONS = [
        [MenuButton('cmd_build', '🏗️', 'Build', 'Create new project', 'cmd_build'),
         MenuButton('cmd_code', '💻', 'Code', 'Generate code', 'cmd_code')],
        [MenuButton('cmd_fix', '🔧', 'Fix', 'Debug and fix issues', 'cmd_fix'),
         MenuButton('cmd_status', '📊', 'Status', 'Check status', 'cmd_status')],
        [MenuButton('cmd_post', '📱', 'Post', 'Social media posting', 'cmd_post'),
         MenuButton('cmd_deploy', '🚀', 'Deploy', 'Deploy project', 'cmd_deploy')],
        [MenuButton('cmd_audit', '🔒', 'Audit', 'Security audit', 'cmd_audit'),
         MenuButton('cmd_learn', '🧠', 'Learn', 'Learning', 'cmd_learn')],
        [MenuButton('cmd_analytics', '📈', 'Analytics', 'Analytics', 'cmd_analytics'),
         MenuButton('cmd_settings', '⚙️', 'Settings', 'Settings', 'cmd_settings')],
        [MenuButton('cmd_skills', '💡', 'Skills', 'Available skills', 'cmd_skills'),
         MenuButton('cmd_heartbeat', '❤️', 'Heartbeat', 'Health check', 'cmd_heartbeat')],
        [MenuButton('cmd_restart', '🔄', 'Restart Agent', 'Restart agent', 'cmd_restart'),
         MenuButton('help_menu', '❓', 'Help', 'Help menu', 'help_menu')]
    ]
    
    PROJECT_MENU_BUTTONS = [
        [MenuButton('proj_python', '🐍', 'Python API', 'Python project', 'proj_python'),
         MenuButton('proj_nodejs', '🟢', 'Node.js API', 'Node.js project', 'proj_nodejs')],
        [MenuButton('proj_react', '⚛️', 'React', 'React app', 'proj_react'),
         MenuButton('proj_typescript', '🔵', 'TypeScript', 'TypeScript project', 'proj_typescript')],
        [MenuButton('back_main', '🏠', 'Main Menu', 'Back to main', 'main_menu')]
    ]
    
    SKILL_CATEGORIES = {
        'code': [
            MenuButton('skill_python', '🐍', 'Python', 'Python coding', 'skill_python'),
            MenuButton('skill_javascript', '🟡', 'JavaScript', 'JavaScript coding', 'skill_javascript'),
        ],
        'analysis': [
            MenuButton('skill_security', '🔒', 'Security Audit', 'Security analysis', 'skill_security'),
            MenuButton('skill_performance', '⚡', 'Performance', 'Performance analysis', 'skill_performance'),
        ],
        'devops': [
            MenuButton('skill_docker', '🐳', 'Docker', 'Docker setup', 'skill_docker'),
            MenuButton('skill_cicd', '🔄', 'CI/CD', 'CI/CD pipeline', 'skill_cicd'),
        ],
        'social': [
            MenuButton('skill_twitter', '🐦', 'Twitter', 'Twitter posting', 'skill_twitter'),
            MenuButton('skill_linkedin', '🔗', 'LinkedIn', 'LinkedIn posting', 'skill_linkedin'),
        ]
    }
    
    def __init__(self):
        self.navigation_history: Dict[int, List[str]] = {}
    
    def get_main_menu_buttons(self) -> List[List[MenuButton]]:
        """Get main menu buttons"""
        return self.MAIN_MENU_BUTTONS
    
    def get_project_menu_buttons(self) -> List[List[MenuButton]]:
        """Get project creation menu buttons"""
        return self.PROJECT_MENU_BUTTONS
    
    def get_skill_buttons(self, category: str) -> List[List[MenuButton]]:
        """Get skill buttons for a category"""
        if category not in self.SKILL_CATEGORIES:
            return []
        buttons = self.SKILL_CATEGORIES[category]
        return [[btn] for btn in buttons] + [[MenuButton('back_menu', '⬅️', 'Back', 'Back', 'main_menu')]]
    
    def format_menu_text(self, title: str, description: str) -> str:
        """Format menu text with title and description"""
        return f"<b>{title}</b>\n\n{description}"
    
    def add_navigation_history(self, user_id: int, menu_id: str):
        """Add menu to navigation history"""
        if user_id not in self.navigation_history:
            self.navigation_history[user_id] = []
        self.navigation_history[user_id].append(menu_id)
    
    def go_back(self, user_id: int) -> Optional[str]:
        """Go back in navigation history"""
        if user_id in self.navigation_history and len(self.navigation_history[user_id]) > 1:
            self.navigation_history[user_id].pop()
            return self.navigation_history[user_id][-1]
        return None


def format_inline_keyboard(buttons: List[List[MenuButton]]) -> Dict:
    """Format buttons into inline keyboard for Telegram"""
    keyboard_buttons = []
    for row in buttons:
        keyboard_row = []
        for btn in row:
            keyboard_row.append({
                'text': f"{btn.emoji} {btn.label}",
                'callback_data': btn.callback_data
            })
        keyboard_buttons.append(keyboard_row)
    
    return {
        'inline_keyboard': keyboard_buttons
    }
