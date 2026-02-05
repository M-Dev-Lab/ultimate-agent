"""
MCP Server Manager - Auto-discovery and Installation
Manages free MCP servers that enhance agent capabilities
"""
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
from datetime import datetime

from app.core.config import settings
from app.core.workflow_logger import WorkflowLogger

logger = logging.getLogger(__name__)

class MCPServerManager:
    """
    Manage MCP servers - discover, install, and use
    Focuses on FREE servers that don't require API keys
    """

    # FREE MCP Servers (No API key required)
    FREE_SERVERS = {
        'web-search': {
            'command': 'npx',
            'args': ['@pskill9/web-search'],
            'capabilities': ['web_search', 'google_search'],
            'category': 'web',
            'description': 'Free Google search without API key',
            'requires_api': False,
            'speed_boost': '100x faster research'
        },
        'duckduckgo-search': {
            'command': 'npx',
            'args': ['duckduckgo-mcp'],
            'capabilities': ['web_search', 'privacy_search'],
            'category': 'web',
            'description': 'Privacy-focused web search',
            'requires_api': False,
            'speed_boost': 'Unlimited queries'
        },
        'firecrawl': {
            'command': 'npx',
            'args': ['@mendable/firecrawl-mcp'],
            'capabilities': ['web_scraping', 'content_extraction'],
            'category': 'web',
            'description': 'Powerful web scraping',
            'requires_api': False,
            'speed_boost': 'Extract any website'
        },
        'playwright': {
            'command': 'npx',
            'args': ['@executeautomation/playwright-mcp-server'],
            'capabilities': ['browser_automation', 'testing'],
            'category': 'browser',
            'description': 'Full browser automation',
            'requires_api': False,
            'speed_boost': 'Complex web interactions'
        },
        'fetch': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-fetch'],
            'capabilities': ['url_fetch', 'content_download'],
            'category': 'web',
            'description': 'Fetch URL content',
            'requires_api': False,
            'speed_boost': 'Instant page access'
        },
        'filesystem': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-filesystem', str(Path(settings.outputs_dir).absolute())],
            'capabilities': ['file_operations', 'directory_management'],
            'category': 'files',
            'description': 'File system operations',
            'requires_api': False,
            'speed_boost': 'Direct file access'
        },
        'git': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-git'],
            'capabilities': ['git_operations', 'version_control'],
            'category': 'development',
            'description': 'Git repository management',
            'requires_api': False,
            'speed_boost': 'Full repo control'
        },
        'memory': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-memory'],
            'capabilities': ['knowledge_graph', 'persistent_memory'],
            'category': 'ai',
            'description': 'Long-term memory system',
            'requires_api': False,
            'speed_boost': 'Remember everything'
        },
        'sequential-thinking': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-sequential-thinking'],
            'capabilities': ['problem_solving', 'reasoning'],
            'category': 'ai',
            'description': 'Enhanced problem-solving',
            'requires_api': False,
            'speed_boost': 'Better decisions'
        },
        'time': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-time'],
            'capabilities': ['time_conversion', 'timezone'],
            'category': 'utility',
            'description': 'Time and timezone tools',
            'requires_api': False,
            'speed_boost': 'Global time handling'
        },
        'sqlite': {
            'command': 'npx',
            'args': ['@modelcontextprotocol/server-sqlite'],
            'capabilities': ['database', 'sql_operations'],
            'category': 'data',
            'description': 'SQLite database operations',
            'requires_api': False,
            'speed_boost': 'Direct DB access'
        },
    }

    def __init__(self):
        self.registry_file = Path(settings.data_dir) / 'mcp_registry.json'
        self.registry = self._load_registry()
        WorkflowLogger.log_system(f"MCP Manager initialized with {len(self.FREE_SERVERS)} available servers")

    def _load_registry(self) -> Dict:
        """Load MCP server registry from disk"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
        return {}

    def _save_registry(self):
        """Save registry to disk"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    async def discover_servers(self, task_description: str, use_ollama: bool = True) -> List[str]:
        """
        Discover which MCP servers are needed for a task
        Uses Ollama Qwen3 (or Claude if available) to analyze task
        """
        WorkflowLogger.log_step("mcp", "discover_servers", f"Analyzing task for MCP needs")

        # Build server catalog
        server_catalog = "\n".join([
            f"- **{name}**: {info['description']} (capabilities: {', '.join(info['capabilities'])})"
            for name, info in self.FREE_SERVERS.items()
        ])

        prompt = f"""Given this task, which MCP servers should be used?

Task: {task_description}

Available FREE MCP Servers (no API keys required):
{server_catalog}

Respond with a JSON array of server names that would be most useful.
Example: ["web-search", "firecrawl", "filesystem"]

Consider:
- Which capabilities are needed
- Speed and efficiency
- No API keys required preference

Only return the JSON array, nothing else.
"""

        try:
            if use_ollama:
                # Use Ollama
                from app.integrations.ollama import get_ollama_client
                ollama = get_ollama_client()
                response = await ollama.generate(
                    model=settings.ollama_model,
                    prompt=prompt,
                    stream=False
                )
                text = response.get('response', '[]')
            elif settings.claude_api_key:
                # Use Claude if available
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.claude_api_key.get_secret_value())
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
            else:
                # Fallback to basic analysis
                return self._basic_server_discovery(task_description)

            # Parse response
            if '```' in text:
                text = text.split('```')[1].replace('json', '').strip()

            recommended = json.loads(text)

            WorkflowLogger.log_success(f"Discovered {len(recommended)} relevant MCP servers")
            return recommended

        except Exception as e:
            WorkflowLogger.log_error("MCP discovery failed", e)
            return self._basic_server_discovery(task_description)

    def _basic_server_discovery(self, task_description: str) -> List[str]:
        """Basic keyword-based server discovery (fallback)"""
        task_lower = task_description.lower()
        servers = []

        # Keyword matching
        if any(word in task_lower for word in ['search', 'google', 'find']):
            servers.append('web-search')

        if any(word in task_lower for word in ['scrape', 'extract', 'crawl']):
            servers.append('firecrawl')

        if any(word in task_lower for word in ['browser', 'automate', 'click']):
            servers.append('playwright')

        if any(word in task_lower for word in ['file', 'directory', 'folder']):
            servers.append('filesystem')

        if any(word in task_lower for word in ['git', 'commit', 'repository']):
            servers.append('git')

        if any(word in task_lower for word in ['time', 'date', 'timezone']):
            servers.append('time')

        if any(word in task_lower for word in ['database', 'sql', 'sqlite']):
            servers.append('sqlite')

        # Always include memory for complex tasks
        if len(task_description) > 100:
            servers.append('memory')

        return list(set(servers))  # Remove duplicates

    async def install_server(self, server_name: str) -> bool:
        """Install an MCP server if not already installed"""
        if server_name not in self.FREE_SERVERS:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        # Check if already installed
        if self.is_installed(server_name):
            WorkflowLogger.log_success(f"MCP server already installed: {server_name}")
            return True

        server_info = self.FREE_SERVERS[server_name]
        WorkflowLogger.log_step("mcp", "install", f"Installing {server_name}")

        try:
            # For npx-based servers, they auto-install on first use
            # Just mark as installed in registry
            self.registry[server_name] = {
                'installed': True,
                'installed_at': datetime.now().isoformat(),
                'command': server_info['command'],
                'args': server_info['args'],
                'capabilities': server_info['capabilities'],
                'last_used': None
            }

            self._save_registry()
            WorkflowLogger.log_success(f"MCP server installed: {server_name}")
            return True

        except Exception as e:
            WorkflowLogger.log_error(f"Failed to install {server_name}", e)
            return False

    def is_installed(self, server_name: str) -> bool:
        """Check if server is installed"""
        return server_name in self.registry and self.registry[server_name].get('installed', False)

    async def use_server(self, server_name: str, action: str, parameters: Dict) -> Dict:
        """
        Use an MCP server (install if needed)
        """
        # Install if needed
        if not self.is_installed(server_name):
            await self.install_server(server_name)

        if server_name not in self.registry:
            return {'success': False, 'error': f'Server {server_name} not available'}

        server_info = self.registry[server_name]

        WorkflowLogger.log_step("mcp", "use_server", f"Using {server_name} for {action}")

        try:
            # Update last used
            self.registry[server_name]['last_used'] = datetime.now().isoformat()
            self._save_registry()

            # Execute server (simplified - in production, use proper MCP protocol)
            result = await self._execute_mcp_action(server_name, action, parameters)

            return result

        except Exception as e:
            WorkflowLogger.log_error(f"Error using {server_name}", e)
            return {'success': False, 'error': str(e)}

    async def _execute_mcp_action(self, server_name: str, action: str, parameters: Dict) -> Dict:
        """
        Execute an MCP action
        (Simplified implementation - full MCP protocol integration needed)
        """
        # This is a placeholder for actual MCP execution
        # In production, implement full MCP stdio protocol communication

        return {
            'success': True,
            'server': server_name,
            'action': action,
            'message': 'MCP action executed (placeholder implementation)',
            'data': parameters
        }

    def get_available_servers(self, category: Optional[str] = None) -> List[Dict]:
        """Get list of available MCP servers"""
        servers = []

        for name, info in self.FREE_SERVERS.items():
            if category and info['category'] != category:
                continue

            server_data = {
                'name': name,
                'description': info['description'],
                'capabilities': info['capabilities'],
                'category': info['category'],
                'speed_boost': info['speed_boost'],
                'installed': self.is_installed(name),
                'requires_api': info['requires_api']
            }

            if name in self.registry:
                server_data['last_used'] = self.registry[name].get('last_used')

            servers.append(server_data)

        return servers

    def get_stats(self) -> Dict:
        """Get MCP manager statistics"""
        total = len(self.FREE_SERVERS)
        installed = sum(1 for s in self.registry.values() if s.get('installed'))

        return {
            'total_available': total,
            'installed': installed,
            'categories': {
                'web': sum(1 for s in self.FREE_SERVERS.values() if s['category'] == 'web'),
                'files': sum(1 for s in self.FREE_SERVERS.values() if s['category'] == 'files'),
                'development': sum(1 for s in self.FREE_SERVERS.values() if s['category'] == 'development'),
                'ai': sum(1 for s in self.FREE_SERVERS.values() if s['category'] == 'ai'),
                'data': sum(1 for s in self.FREE_SERVERS.values() if s['category'] == 'data'),
            }
        }
