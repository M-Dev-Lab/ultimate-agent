"""
Skill Registry for Ultimate Coding Agent
Integrates with Sampling Projects/OpenClaw skills framework
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from app.core.config import settings
from app.integrations.ollama import get_ollama_client

logger = structlog.get_logger(__name__)


@dataclass
class Skill:
    """Skill definition"""
    name: str
    slug: str
    category: str
    description: str
    path: str
    prompt_template: str = ""
    use_count: int = 0
    success_rate: float = 0.0
    installed_at: Optional[datetime] = None


@dataclass
class SkillExecutionResult:
    """Result of skill execution"""
    success: bool
    output: str
    skill: str
    duration_ms: float
    model_used: str
    error: Optional[str] = None


class SkillRegistry:
    """Python skill registry that mirrors TypeScript skill manager"""
    
    def __init__(self):
        self.skills_dir = Path(__file__).parent.parent.parent / "skills"
        self.sampling_dir = Path("/home/zeds/Desktop/ultimate-agent/Sampling Projects /openclaw-main/src/agents/skills")
        self.installed_skills: Dict[str, Skill] = {}
        self.skill_prompts: Dict[str, str] = {}
        
        # Load skills from resources
        self._load_sampling_skills()
        self._load_builtin_skills()
    
    def _load_sampling_skills(self):
        """Load skills from Sampling Projects/OpenClaw"""
        try:
            # Load skill types and prompts from OpenClaw
            types_file = self.sampling_dir / "types.ts"
            workspace_file = self.sampling_dir / "workspace.ts"
            
            logger.info(f"📚 Loading skills from {self.sampling_dir}")
            
            # Register built-in OpenClaw-inspired skills
            self._register_builtin_skills()
            
        except Exception as e:
            logger.warning(f"Could not load sampling skills: {e}")
    
    def _register_builtin_skills(self):
        """Register built-in skills with prompt templates"""
        
        # Code Generation Skills
        self.register_skill(Skill(
            name="Python Web API",
            slug="python-web-api",
            category="code",
            description="Generate Python FastAPI/Flask web APIs",
            path="builtin",
            prompt_template="""You are an expert Python developer. Generate a complete {project_name} API with:

Requirements:
- Framework: {framework}
- Language: Python 3.10+
- Include: models, routes, schemas, validation
- Follow best practices: type hints, docstrings, error handling

Project: {description}

Generate ONLY the code, organized by files."""
        ))
        
        self.register_skill(Skill(
            name="JavaScript Node.js",
            slug="nodejs-api",
            category="code",
            description="Generate Node.js Express APIs",
            path="builtin",
            prompt_template="""You are an expert Node.js developer. Generate a complete {project_name} API with:

Requirements:
- Framework: Express.js
- Language: JavaScript/TypeScript
- Include: routes, controllers, models, middleware
- Follow RESTful conventions

Project: {description}

Generate the complete project structure."""
        ))
        
        self.register_skill(Skill(
            name="React Component",
            slug="react-component",
            category="code",
            description="Generate React components",
            path="builtin",
            prompt_template="""You are a React expert. Generate a {component_name} component:

Requirements:
- Framework: React 18+
- Style: {style}
- Features: {features}
- Include: props, state, effects, handlers

Generate clean, modern React code with proper TypeScript types."""
        ))
        
        # Analysis Skills
        self.register_skill(Skill(
            name="Code Security Audit",
            slug="security-audit",
            category="analysis",
            description="Perform security analysis on code",
            path="builtin",
            prompt_template="""Perform a comprehensive SECURITY AUDIT on this code:

```{language}
{code}
```

Analyze for:
1. SQL injection vulnerabilities
2. XSS vulnerabilities
3. Authentication/authorization issues
4. Data exposure risks
5. Dependency vulnerabilities
6. Input validation issues

Provide findings in this format:
- [HIGH/MEDIUM/LOW] Vulnerability: description and location
- Recommendation for each issue
- Severity score (0-100)

Focus on actionable security improvements."""
        ))
        
        self.register_skill(Skill(
            name="Performance Analysis",
            slug="perf-analysis",
            category="analysis",
            description="Analyze code performance",
            path="builtin",
            prompt_template="""Analyze this code for performance issues:

```{language}
{code}
```

Check for:
1. Time complexity issues
2. Memory leaks
3. Inefficient algorithms
4. Unnecessary computations
5. I/O bottlenecks

Provide recommendations with code examples."""
        ))
        
        # DevOps Skills
        self.register_skill(Skill(
            name="Docker Configuration",
            slug="docker-config",
            category="devops",
            description="Generate Docker configurations",
            path="builtin",
            prompt_template="""Generate Docker configuration for this project:

Project: {project_name}
Type: {project_type}
Language: {language}

Generate:
1. Dockerfile with best practices
2. .dockerignore
3. docker-compose.yml (if applicable)
4. Entry point configuration

Use multi-stage builds when appropriate."""
        ))
        
        self.register_skill(Skill(
            name="CI/CD Pipeline",
            slug="cicd-pipeline",
            category="devops",
            description="Generate CI/CD pipelines",
            path="builtin",
            prompt_template="""Generate CI/CD pipeline for:

Project: {project_name}
Language: {language}
Platform: {platform} (github/gitlab/azure)

Generate:
1. Pipeline configuration
2. Test commands
3. Build steps
4. Deployment configuration (if applicable)"""
        ))
        
        # Documentation Skills
        self.register_skill(Skill(
            name="API Documentation",
            slug="api-docs",
            category="docs",
            description="Generate API documentation",
            path="builtin",
            prompt_template="""Generate comprehensive API documentation for:

API: {api_name}
Framework: {framework}
Endpoints:
{endpoints}

Format: OpenAPI/Swagger specification with:
- Endpoint descriptions
- Request/response schemas
- Authentication requirements
- Example requests"""
        ))
        
        # Testing Skills
        self.register_skill(Skill(
            name="Unit Tests",
            slug="unit-tests",
            category="testing",
            description="Generate unit tests",
            path="builtin",
            prompt_template="""Generate comprehensive unit tests for:

Language: {language}
Framework: {test_framework}
Code:
```{language}
{code}
```

Generate tests covering:
- Happy path scenarios
- Edge cases
- Error handling
- Mocks/stubs where needed

Use pytest/unittest conventions."""
        ))
        
        # Social/Post Skills
        self.register_skill(Skill(
            name="Dev Blog Post",
            slug="blog-post",
            category="social",
            description="Generate developer blog posts",
            path="builtin",
            prompt_template="""Write a developer blog post about:

Topic: {topic}
Tone: {tone} (technical/casual)
Length: {length} (short/medium/long)
Audience: {audience} (junior/senior/mixed)

Include:
- Engaging introduction
- Technical deep-dives with code examples
- Best practices
- References to official docs

Format: Markdown with code blocks."""
        ))
        
        self.register_skill(Skill(
            name="GitHub README",
            slug="github-readme",
            category="social",
            description="Generate GitHub README",
            path="builtin",
            prompt_template="""Generate a professional GitHub README for:

Project: {project_name}
Type: {project_type}
Description: {description}
Features: {features}
Tech Stack: {tech_stack}

Include:
- Badges (build, license, coverage)
- Installation instructions
- Usage examples
- Contributing guidelines
- License"""
        ))
        
        logger.info(f"📦 Registered {len(self.installed_skills)} skills")
    
    def _load_builtin_skills(self):
        """Load built-in skill templates"""
        pass
    
    def register_skill(self, skill: Skill):
        """Register a skill in the registry"""
        self.installed_skills[skill.slug] = skill
        logger.debug(f"Registered skill: {skill.name} ({skill.slug})")
    
    async def execute_skill(
        self,
        skill_slug: str,
        params: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> SkillExecutionResult:
        """Execute a skill using Ollama"""
        import time
        start_time = time.time()
        
        skill = self.installed_skills.get(skill_slug)
        if not skill:
            return SkillExecutionResult(
                success=False,
                output="",
                skill=skill_slug,
                duration_ms=0,
                model_used="",
                error=f"Skill not found: {skill_slug}"
            )
        
        # Build prompt from template
        prompt = self._build_prompt(skill.prompt_template, params)
        
        try:
            ollama = get_ollama_client()
            result = await ollama.generate(
                prompt=prompt,
                temperature=0.7
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Update usage stats
            skill.use_count += 1
            
            return SkillExecutionResult(
                success=True,
                output=result,
                skill=skill_slug,
                duration_ms=duration_ms,
                model_used=ollama.local_model if not ollama.is_cloud else "cloud"
            )
            
        except Exception as e:
            return SkillExecutionResult(
                success=False,
                output="",
                skill=skill_slug,
                duration_ms=(time.time() - start_time) * 1000,
                model_used="",
                error=str(e)
            )
    
    def _build_prompt(self, template: str, params: Dict) -> str:
        """Fill in prompt template with params"""
        return template.format(**params)
    
    def list_skills(self, category: Optional[str] = None) -> List[Dict]:
        """List skills, optionally filtered by category"""
        skills = []
        for skill in self.installed_skills.values():
            if not category or skill.category == category:
                skills.append({
                    "name": skill.name,
                    "slug": skill.slug,
                    "category": skill.category,
                    "description": skill.description,
                    "use_count": skill.use_count
                })
        return skills
    
    def get_categories(self) -> List[Dict]:
        """Get all skill categories"""
        categories = {}
        for skill in self.installed_skills.values():
            if skill.category not in categories:
                categories[skill.category] = {
                    "name": skill.category,
                    "count": 0,
                    "skills": []
                }
            categories[skill.category]["count"] += 1
            categories[skill.category]["skills"].append(skill.slug)
        return list(categories.values())


# Global registry
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create skill registry"""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
