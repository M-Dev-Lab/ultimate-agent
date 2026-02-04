"""
Project Manager Skill for Ultimate Coding Agent
Creates complete project structures with AI-generated code
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any
from app.skills.base_skill import BaseSkill, SkillResult
from app.integrations.ollama import get_ollama_client
import structlog

logger = structlog.get_logger(__name__)


class ProjectManagerSkill(BaseSkill):
    """Create and manage software projects"""
    
    name = "project_manager"
    description = "Create complete software projects with code generation"
    category = "development"
    
    PROJECT_TEMPLATES = {
        "python": {
            "fastapi": {
                "files": {
                    "main.py": """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="{project_name}", version="1.0.0")

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

items: List[Item] = []

@app.get("/")
async def root():
    return {{"message": "Welcome to {project_name}", "version": "1.0.0"}}

@app.get("/items")
async def get_items():
    return items

@app.get("/items/{{item_id}}")
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items")
async def create_item(item: Item):
    items.append(item)
    return item

@app.delete("/items/{{item_id}}")
async def delete_item(item_id: int):
    for i, item in enumerate(items):
        if item.id == item_id:
            deleted = items.pop(i)
            return {{"deleted": deleted}}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""",
                    "requirements.txt": """fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
""",
                    "README.md": """# {project_name}

{project_description}

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## API Endpoints

- `GET /` - Root
- `GET /items` - List all items
- `POST /items` - Create item
- `GET /items/{{id}}` - Get item
- `DELETE /items/{{id}}` - Delete item
""",
                    ".gitignore": """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env
.DS_Store
""",
                }
            },
            "flask": {
                "files": {
                    "app.py": """from flask import Flask, jsonify, request

app = Flask(__name__)

items = []

@app.route('/')
def index():
    return jsonify({{"message": "Welcome to {project_name}"}})

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(items)

@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    items.append(data)
    return jsonify(data), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
""",
                    "requirements.txt": """Flask==3.0.0
""",
                    "README.md": "# {project_name}\n\n{project_description}",
                    ".gitignore": "__pycache__/\nvenv/\n.env",
                }
            },
        },
        "javascript": {
            "express": {
                "files": {
                    "index.js": """const express = require('express');
const app = express();
const port = 3000;

app.use(express.json());

let items = [];

app.get('/', (req, res) => {{
    res.json({{ message: 'Welcome to {project_name}' }});
}});

app.get('/items', (req, res) => {{
    res.json(items);
}});

app.post('/items', (req, res) => {{
    const item = req.body;
    items.push(item);
    res.status(201).json(item);
}});

app.listen(port, () => {{
    console.log(`Server running on port ${{port}}`);
}});
""",
                    "package.json": """{{
  "name": "{project_name}",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {{
    "start": "node index.js"
  }},
  "dependencies": {{
    "express": "^4.18.2"
  }}
}}
""",
                    "README.md": "# {project_name}\n\n{project_description}",
                    ".gitignore": "node_modules/\n.env\n.DS_Store",
                }
            },
        },
        "typescript": {
            "express": {
                "files": {
                    "src/index.ts": """import express, { Request, Response } from 'express';
const app = express();
const port = 3000;

app.use(express.json());

interface Item {{
    id: number;
    name: string;
}}

let items: Item[] = [];

app.get('/', (req: Request, res: Response) => {{
    res.json({{ message: 'Welcome to {project_name}' }});
}});

app.get('/items', (req: Request, res: Response) => {{
    res.json(items);
}});

app.post('/items', (req: Request, res: Response) => {{
    const item: Item = req.body;
    items.push(item);
    res.status(201).json(item);
}});

app.listen(port, () => {{
    console.log(`Server running on port ${{port}}`);
}});
""",
                    "package.json": """{{
  "name": "{project_name}",
  "version": "1.0.0",
  "main": "dist/index.js",
  "scripts": {{
    "build": "tsc",
    "start": "node dist/index.js"
  }},
  "dependencies": {{
    "express": "^4.18.2"
  }},
  "devDependencies": {{
    "typescript": "^5.3.3",
    "@types/express": "^4.17.21",
    "@types/node": "^20.10.6"
  }}
}}
""",
                    "tsconfig.json": """{{
  "compilerOptions": {{
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true
  }},
  "include": ["src/**/*"]
}}
""",
                    "README.md": "# {project_name}\n\n{project_description}",
                    ".gitignore": "node_modules/\ndist/\n.env\n.DS_Store",
                }
            },
        },
    }
    
    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute project creation"""
        project_name = params.get("project_name", "unnamed_project")
        language = params.get("language", "python")
        framework = params.get("framework", "fastapi")
        goal = params.get("goal", "Create a new project")
        
        workspace_dir = Path(params.get("workspace_dir", "./data/workspaces"))
        project_path = workspace_dir / project_name
        
        try:
            project_path.mkdir(parents=True, exist_ok=True)
            
            template_key = framework if language == "python" else framework
            
            if language not in self.PROJECT_TEMPLATES:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Unsupported language: {language}"
                )
            
            lang_templates = self.PROJECT_TEMPLATES[language]
            
            if framework not in lang_templates:
                framework = list(lang_templates.keys())[0]
            
            template_files = lang_templates[framework]["files"]
            
            for filename, content in template_files.items():
                if language == "typescript" and filename == "src/index.ts":
                    file_path = project_path / filename
                else:
                    file_path = project_path / filename
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_content = content.format(
                    project_name=project_name,
                    project_description=goal
                )
                
                file_path.write_text(file_content)
            
            if language == "typescript":
                (project_path / "src").mkdir(exist_ok=True)
            
            logger.info(f"Project created: {project_path}")
            
            return SkillResult(
                success=True,
                output=f"✅ Project '{project_name}' created successfully!\n\n"
                       f"Location: {project_path}\n"
                       f"Language: {language}\n"
                       f"Framework: {framework}\n\n"
                       f"Files created:\n" +
                       "\n".join([f"  - {f}" for f in template_files.keys()]),
                data={
                    "project_name": project_name,
                    "project_path": str(project_path),
                    "language": language,
                    "framework": framework,
                    "files": list(template_files.keys())
                }
            )
            
        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def generate_code_ai(self, goal: str, language: str, context: str = "") -> str:
        """Generate additional code using AI"""
        ollama = get_ollama_client()
        
        prompt = f"""Generate {language} code for the following requirement:

{goal}

Context: {context}

Generate ONLY the code, no explanations. Use best practices and proper error handling."""

        try:
            result = await ollama.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            return result
        except Exception as e:
            logger.error(f"AI code generation failed: {e}")
            return ""
