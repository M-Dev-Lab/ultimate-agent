"""
Agent Brain - Makes intelligent decisions using Ollama Qwen3 Coder
Decision-making engine for the autonomous agent
"""
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path

from app.core.config import settings
from app.core.workflow_logger import WorkflowLogger
from app.integrations.ollama import get_ollama_client

logger = logging.getLogger(__name__)

class AgentBrain:
    """
    Decision-making engine using Ollama Qwen3 Coder
    Analyzes situations and determines best course of action
    """

    def __init__(self):
        self.ollama = get_ollama_client()
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict:
        """Load agent memory from files"""
        memory = {}

        memory_files = {
            'soul': Path(settings.memory_dir) / 'SOUL.md',
            'identity': Path(settings.memory_dir) / 'IDENTITY.md',
            'memory': Path(settings.memory_dir) / 'MEMORY.md',
        }

        for key, path in memory_files.items():
            if path.exists():
                memory[key] = path.read_text()
            else:
                memory[key] = ""

        return memory

    async def analyze_request(self, request: str, context: Dict = None) -> Dict:
        """
        Analyze a request and determine what to do

        Returns:
            {
                'action': 'code_generation' | 'system_command' | 'browser_automation' | etc,
                'parameters': {...},
                'reasoning': 'why this action was chosen',
                'priority': 'high' | 'medium' | 'low'
            }
        """
        WorkflowLogger.log_step("brain", "analyze_request", f"Analyzing: {request[:100]}")

        prompt = self._build_analysis_prompt(request, context)

        try:
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            # Parse Ollama's response
            analysis = self._parse_analysis(response.get('response', ''))

            WorkflowLogger.log_success(f"Analysis complete: {analysis['action']}")
            return analysis

        except Exception as e:
            WorkflowLogger.log_error("Analysis failed", e)
            return {
                'action': 'error',
                'error': str(e),
                'reasoning': 'Failed to analyze request'
            }

    def _build_analysis_prompt(self, request: str, context: Dict = None) -> str:
        """Build prompt for Ollama to analyze the request"""
        prompt = f"""You are an autonomous AI agent assistant with senior developer capabilities.
You operate on a local Linux machine and help the admin user complete tasks.

## Your Capabilities:
1. **Code Generation** - Create complete projects, fix bugs, write documentation
2. **System Control** - Execute shell commands, manage processes, monitor system
3. **Browser Automation** - Scrape data, automate web tasks, test websites
4. **File Operations** - Create/modify projects in {settings.outputs_dir}
5. **Research** - Search web, compile information, analyze data
6. **Project Management** - Create full applications from descriptions

## Your Personality (from SOUL.md):
{self.memory.get('soul', 'Senior developer, proactive, detail-oriented')}

## User Profile (from IDENTITY.md):
{self.memory.get('identity', 'Admin user preferences')}

## Request to Analyze:
{request}

## Context:
{json.dumps(context or {}, indent=2)}

## Your Task:
Analyze this request and determine the best action to take.

Respond ONLY with a JSON object in this exact format:
{{
  "action": "one of: code_generation, system_command, browser_automation, project_creation, research, multi_step_workflow, file_operation, analysis",
  "parameters": {{
    // specific parameters for the action
    // For code_generation: {{"language": "python", "project_type": "web_app", "description": "..."}}
    // For system_command: {{"command": "git status", "safe": true}}
    // For browser_automation: {{"url": "https://...", "action": "scrape"}}
  }},
  "reasoning": "brief explanation of why you chose this action (1-2 sentences)",
  "priority": "high, medium, or low",
  "estimated_time_minutes": 10
}}

Be precise and actionable. Choose the most efficient approach.
Always ensure actions are safe and within the system's capabilities.
"""
        return prompt

    def _parse_analysis(self, response: str) -> Dict:
        """Parse Ollama's JSON response"""
        # Extract JSON from markdown code blocks if present
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            response = response[start:end].strip()
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            response = response[start:end].strip()

        try:
            parsed = json.loads(response)
            # Ensure required fields
            if 'action' not in parsed:
                parsed['action'] = 'manual_review'
            if 'reasoning' not in parsed:
                parsed['reasoning'] = 'AI analysis completed'
            if 'priority' not in parsed:
                parsed['priority'] = 'medium'
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            # Fallback parsing
            return {
                'action': 'manual_review',
                'reasoning': 'Could not parse response',
                'priority': 'medium',
                'raw_response': response
            }

    async def make_decision(self, situation: str, options: List[Dict]) -> Dict:
        """
        Make a decision between multiple options
        """
        prompt = f"""Given the following situation, choose the best option:

Situation: {situation}

Options:
{json.dumps(options, indent=2)}

Respond with a JSON object:
{{
  "choice": 0,  # index of best option (0-{len(options)-1})
  "reasoning": "explain why this is the best choice",
  "confidence": "high, medium, or low"
}}
"""

        WorkflowLogger.log_ai_action("make_decision", prompt)

        try:
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            decision = self._parse_analysis(response.get('response', ''))
            return decision

        except Exception as e:
            logger.error(f"Decision-making error: {e}")
            return {
                'choice': 0,  # Default to first option
                'reasoning': f'Error making decision: {str(e)}',
                'confidence': 'low'
            }

    async def plan_project(self, description: str, requirements: List[str] = None) -> Dict:
        """
        Create a detailed plan for a project
        """
        prompt = f"""You are a senior software architect. Plan a complete project.

## Project Description:
{description}

## Requirements:
{json.dumps(requirements or [], indent=2)}

## Create a detailed project plan as JSON:
{{
  "project_name": "name-in-kebab-case",
  "description": "brief description",
  "tech_stack": ["python", "fastapi", "..."],
  "directory_structure": {{
    "src/": ["main.py", "config.py", "..."],
    "tests/": ["test_main.py", "..."]
  }},
  "files_to_create": [
    {{
      "path": "src/main.py",
      "purpose": "entry point",
      "dependencies": []
    }}
  ],
  "implementation_steps": [
    "1. Set up project structure",
    "2. Create configuration",
    "..."
  ],
  "estimated_time_hours": 4,
  "complexity": "low, medium, or high"
}}
"""

        WorkflowLogger.log_ai_action("plan_project", prompt)

        try:
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            plan = self._parse_analysis(response.get('response', ''))
            return plan

        except Exception as e:
            logger.error(f"Project planning error: {e}")
            return {
                'error': str(e),
                'project_name': 'unnamed-project',
                'description': description
            }

    async def debug_error(self, error_message: str, code_context: str) -> Dict:
        """
        Analyze and suggest fixes for errors
        """
        prompt = f"""You are debugging an error. Analyze and provide a fix.

## Error Message:
{error_message}

## Code Context:
```
{code_context}
```

## Provide analysis as JSON:
{{
  "error_type": "syntax | runtime | logic | dependency",
  "root_cause": "explanation of what's causing the error",
  "suggested_fix": "code or steps to fix it",
  "prevention": "how to prevent this in future"
}}
"""

        WorkflowLogger.log_ai_action("debug_error", prompt)

        try:
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            debug_info = self._parse_analysis(response.get('response', ''))
            return debug_info

        except Exception as e:
            logger.error(f"Debug error: {e}")
            return {
                'error': str(e),
                'error_type': 'unknown',
                'root_cause': 'Could not analyze error'
            }

    async def generate_code(self, description: str, language: str = "python") -> Dict:
        """
        Generate code based on description
        """
        prompt = f"""Generate {language} code for the following:

Description: {description}

Requirements:
- Write clean, well-documented code
- Include error handling
- Follow best practices for {language}
- Make it production-ready

Provide response as JSON:
{{
  "code": "the complete code",
  "filename": "suggested_filename.{language}",
  "dependencies": ["list", "of", "dependencies"],
  "usage_instructions": "how to use this code"
}}
"""

        WorkflowLogger.log_ai_action("generate_code", prompt)

        try:
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            code_info = self._parse_analysis(response.get('response', ''))
            return code_info

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {
                'error': str(e),
                'code': '',
                'filename': f'generated.{language}'
            }

    def update_memory(self, key: str, content: str):
        """Update agent memory"""
        memory_file = Path(settings.memory_dir) / f"{key.upper()}.md"
        try:
            with open(memory_file, 'a') as f:
                f.write(f"\n\n---\n{content}\n")
            self.memory[key] = self._load_memory().get(key, "")
            WorkflowLogger.log_success(f"Memory updated: {key}")
        except Exception as e:
            WorkflowLogger.log_error(f"Failed to update memory: {key}", e)
