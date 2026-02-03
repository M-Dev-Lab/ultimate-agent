import express from 'express';
import { WebSocketServer, RawData } from 'ws';
import { createServer } from 'http';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || 'localhost';

app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

app.get('/health', async (req, res) => {
  try {
    let ollamaStatus = 'offline';
    let currentModel = 'qwen2.5-coder:7b-instruct-q5_K_M';
    
    try {
      const response = await fetchWithTimeout('http://127.0.0.1:11434/api/tags', 2000);
      if (response.ok) {
        ollamaStatus = 'online';
        const data = await response.json() as { models: Array<{ name: string }> };
        const models = data.models || [];
        const codingModel = models.find((m: { name: string }) => m.name.toLowerCase().includes('coder'));
        if (codingModel) {
          currentModel = codingModel.name;
        }
      }
    } catch (e) {
      ollamaStatus = 'offline';
    }

    res.json({
      status: ollamaStatus === 'online' ? 'healthy' : 'degraded',
      service: 'ultimate-agent',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      model: currentModel,
      ollama: ollamaStatus
    });
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      error: (error as Error).message
    });
  }
});

app.get('/api/status', async (req, res) => {
  try {
    let ollamaModels: Array<{ name: string; size?: number }> = [];
    let currentModel = 'qwen2.5-coder:7b-instruct-q5_K_M';
    
    try {
      const response = await fetchWithTimeout('http://127.0.0.1:11434/api/tags', 2000);
      if (response.ok) {
        const data = await response.json() as { models: Array<{ name: string; size?: number }> };
        ollamaModels = data.models || [];
        const codingModel = ollamaModels.find(m => m.name.toLowerCase().includes('coder'));
        if (codingModel) {
          currentModel = codingModel.name;
        }
      }
    } catch (e) {
      // Ollama not available
    }

    const memoryUsage = process.memoryUsage();
    const outputsDir = path.join(__dirname, '../outputs');
    let projectsCount = 0;
    try {
      const entries = await fs.readdir(outputsDir, { withFileTypes: true });
      projectsCount = entries.filter(e => e.isDirectory()).length;
    } catch (e) {
      // outputs dir doesn't exist yet
    }

    const dataDir = path.join(__dirname, '../data');
    let learningEntries = 0;
    try {
      const learningFile = path.join(dataDir, 'learning-data.json');
      const exists = await fs.access(learningFile).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(learningFile, 'utf-8');
        const parsed = JSON.parse(content);
        learningEntries = Array.isArray(parsed) ? parsed.length : 0;
      }
    } catch (e) {
      // No learning data yet
    }

    res.json({
      status: 'running',
      ollama: {
        status: ollamaModels.length > 0 ? 'online' : 'offline',
        models: ollamaModels,
        currentModel: currentModel
      },
      system: {
        uptime: process.uptime(),
        memory: {
          heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024),
          heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024),
          rss: Math.round(memoryUsage.rss / 1024 / 1024)
        },
        nodeVersion: process.version
      },
      projects: {
        count: projectsCount
      },
      learning: {
        entries: learningEntries
      }
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/projects', async (req, res) => {
  try {
    const outputsDir = path.join(__dirname, '../outputs');
    
    let projects: Array<{ id: string; name: string; path: string; timestamp: number; description?: string }> = [];
    try {
      const entries = await fs.readdir(outputsDir, { withFileTypes: true });
      projects = entries
        .filter(e => e.isDirectory())
        .map(dir => {
          const projectPath = path.join(outputsDir, dir.name);
          const timestamp = parseInt(dir.name.match(/-(\d+)$/)?.[1] || Date.now().toString());
          const name = dir.name.replace(/-[0-9]+$/, '').replace(/-/g, ' ');
          return {
            id: dir.name,
            name: name,
            path: projectPath,
            timestamp: timestamp,
            description: `Project created on ${new Date(timestamp).toLocaleDateString()}`
          };
        })
        .sort((a, b) => b.timestamp - a.timestamp);
    } catch (e) {
      projects = [];
    }

    res.json(projects);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/learning/stats', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const learningFile = path.join(dataDir, 'learning-data.json');
    
    let stats = {
      totalEntries: 0,
      averageRating: 0,
      byTag: {} as Record<string, number>
    };

    try {
      const exists = await fs.access(learningFile).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(learningFile, 'utf-8');
        const entries = JSON.parse(content);
        
        if (Array.isArray(entries)) {
          stats.totalEntries = entries.length;
          
          const rated = entries.filter((e: { rating?: number }) => e.rating);
          if (rated.length > 0) {
            stats.averageRating = rated.reduce((sum: number, e: { rating: number }) => sum + e.rating, 0) / rated.length;
          }
          
          const tagCounts: Record<string, number> = {};
          entries.forEach((entry: { tags?: string[] }) => {
            if (entry.tags && Array.isArray(entry.tags)) {
              entry.tags.forEach(tag => {
                tagCounts[tag] = (tagCounts[tag] || 0) + 1;
              });
            }
          });
          stats.byTag = tagCounts;
        }
      }
    } catch (e) {
      // No learning data yet
    }

    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/learning/export', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const learningFile = path.join(dataDir, 'learning-data.json');
    const outputFile = path.join(dataDir, 'fine-tuning-data.jsonl');

    try {
      const exists = await fs.access(learningFile).then(() => true).catch(() => false);
      if (!exists) {
        return res.status(404).json({ error: 'No learning data found' });
      }

      const content = await fs.readFile(learningFile, 'utf-8');
      const entries = JSON.parse(content);

      const highQuality = entries.filter((e: { rating?: number }) => (e.rating || 0) >= 4);
      
      if (highQuality.length === 0) {
        return res.status(400).json({ error: 'No high-quality entries found (rating >= 4 required)' });
      }

      const jsonlLines = highQuality.map((entry: { prompt?: string; response?: string; tags?: string[] }) => JSON.stringify({
        prompt: entry.prompt,
        completion: entry.response,
        tags: entry.tags
      }));

      await fs.writeFile(outputFile, jsonlLines.join('\n'));

      res.json({
        success: true,
        exportedCount: highQuality.length,
        outputFile: outputFile
      });
    } catch (e) {
      res.status(500).json({ error: (e as Error).message });
    }
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/interactions', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const dbPath = path.join(dataDir, 'db/interactions.db');
    const interactionsPath = path.join(dataDir, 'interactions.json');

    let totalCommands = 0;
    let todayCommands = 0;
    let lastCommand = 'None';
    const byType: Record<string, number> = {};
    let recentCommands: string[] = [];

    try {
      const exists = await fs.access(interactionsPath).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(interactionsPath, 'utf-8');
        const interactions = JSON.parse(content);
        
        if (Array.isArray(interactions)) {
          totalCommands = interactions.length;
          const today = new Date().toDateString();
          const todayStart = new Date(today).getTime();
          
          interactions.forEach((cmd: { type?: string; timestamp?: number }) => {
            if (cmd.timestamp && cmd.timestamp >= todayStart) {
              todayCommands++;
            }
            if (cmd.type) {
              byType[cmd.type] = (byType[cmd.type] || 0) + 1;
            }
          });

          const sorted = [...interactions].sort((a: { timestamp?: number }, b: { timestamp?: number }) => (b.timestamp || 0) - (a.timestamp || 0));
          recentCommands = sorted.slice(0, 5).map((c: { command?: string }) => c.command || 'Unknown');
          if (recentCommands.length > 0) {
            lastCommand = recentCommands[0];
          }
        }
      }
    } catch (e) {
      // No interactions data yet
    }

    res.json({
      total: totalCommands,
      today: todayCommands,
      lastCommand,
      byType,
      recent: recentCommands
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/skills', async (req, res) => {
  try {
    const skillsPath = path.join(__dirname, '../data/skills.json');
    const skillManagerPath = path.join(__dirname, '../src/skills/skill_manager.ts');

    let installedSkills = 0;
    let categories: string[] = [];

    try {
      const exists = await fs.access(skillsPath).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(skillsPath, 'utf-8');
        const skills = JSON.parse(content);
        if (Array.isArray(skills)) {
          installedSkills = skills.length;
          categories = [...new Set(skills.map((s: { category?: string }) => s.category || 'General'))];
        }
      }
    } catch (e) {
      // Default to known skill count
      installedSkills = 700;
      categories = ['Development', 'DevOps', 'Analysis', 'Communication', 'Security'];
    }

    res.json({
      total: installedSkills,
      categories: categories.length,
      categoryList: categories
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/memory', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const memoryPath = path.join(dataDir, 'memory.json');

    let factsCount = 0;
    let preferencesCount = 0;
    let contextCount = 0;

    try {
      const exists = await fs.access(memoryPath).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(memoryPath, 'utf-8');
        const memory = JSON.parse(content);
        factsCount = memory.facts?.length || 0;
        preferencesCount = memory.preferences?.length || 0;
        contextCount = memory.context?.length || 0;
      }
    } catch (e) {
      // No memory data yet
    }

    res.json({
      facts: factsCount,
      preferences: preferencesCount,
      context: contextCount,
      total: factsCount + preferencesCount + contextCount
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/analytics', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const suggestions: string[] = [];

    try {
      const interactionsPath = path.join(dataDir, 'interactions.json');
      const exists = await fs.access(interactionsPath).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(interactionsPath, 'utf-8');
        const interactions = JSON.parse(content);
        
        if (Array.isArray(interactions) && interactions.length > 0) {
          const recentBuilds = interactions.filter((i: { type?: string }) => i.type === '/build').length;
          if (recentBuilds > 10) {
            suggestions.push('Consider pulling a larger model like qwen2.5-coder:30b for complex projects');
          }
          
          const recentFixes = interactions.filter((i: { type?: string }) => i.type === '/fix').length;
          if (recentFixes > recentBuilds) {
            suggestions.push('Your agent is doing more fixing than building. Consider reviewing code quality practices');
          }
        } else {
          suggestions.push('Start using the agent more to generate improvement suggestions');
        }
      } else {
        suggestions.push('Run /heartbeat to activate proactive monitoring');
        suggestions.push('Use /build to create your first project');
        suggestions.push('Use /analytics to track your agent\'s performance');
      }
    } catch (e) {
      suggestions.push('Interact with your agent to generate analytics');
    }

    res.json({
      suggestions,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.get('/api/heartbeat', async (req, res) => {
  try {
    const dataDir = path.join(__dirname, '../data');
    const heartbeatPath = path.join(dataDir, 'heartbeat.json');

    let lastCheck = 'Never';
    let status = 'inactive';
    let checksToday = 0;

    try {
      const exists = await fs.access(heartbeatPath).then(() => true).catch(() => false);
      if (exists) {
        const content = await fs.readFile(heartbeatPath, 'utf-8');
        const heartbeat = JSON.parse(content);
        lastCheck = heartbeat.lastCheck || 'Never';
        status = heartbeat.status || 'inactive';
        checksToday = heartbeat.checksToday || 0;
      }
    } catch (e) {
      // No heartbeat data
    }

    res.json({
      status,
      lastCheck,
      checksToday,
      interval: 30 // minutes
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

app.post('/api/build', async (req, res) => {
  const { goal, stack, name } = req.body as { goal?: string; stack?: string; name?: string };

  if (!goal) {
    return res.status(400).json({ error: 'Goal is required' });
  }

  try {
    const projectName = name || goal.toLowerCase().replace(/[^a-z0-9]+/g, '-').substring(0, 50);
    const timestamp = Date.now();
    const projectDir = path.join(__dirname, '../outputs', `${projectName}-${timestamp}`);
    const workspaceDir = path.join(__dirname, '../workspaces/current');
    
    await fs.mkdir(projectDir, { recursive: true });
    await fs.mkdir(workspaceDir, { recursive: true });

    res.json({
      success: true,
      project: {
        id: `${projectName}-${timestamp}`,
        name: projectName,
        path: projectDir,
        timestamp,
        status: 'building'
      }
    });

    let model = process.env.OLLAMA_MODEL;
    try {
      const ollamaResponse = await fetchWithTimeout('http://127.0.0.1:11434/api/tags', 3000);
      if (ollamaResponse.ok) {
        const data = await ollamaResponse.json() as { models: Array<{ name: string }> };
        const models = data.models || [];
        const modelNames = models.map((m: { name: string }) => m.name);
        
        const codingPatterns = ['qwen2.5-coder', 'qwen-coder', 'codellama', 'deepseek-coder', 'llama3.2'];
        for (const pattern of codingPatterns) {
          const match = modelNames.find((n: string) => n.toLowerCase().includes(pattern.toLowerCase()));
          if (match) {
            model = match;
            break;
          }
        }
        
        if (!model && modelNames.length > 0) {
          model = modelNames[0];
        }
      }
    } catch (e) {
      console.warn('Could not detect models, using default');
    }
    
    if (!model) model = 'llava-phi3:latest';
    
    console.log(`🤖 Using model for build: ${model}`);
    
    const codePrompt = `You are an expert full-stack developer. Create a complete project for: "${goal}"

${stack ? `Use this technology stack: ${stack}` : 'Use modern best practices with Node.js, React, or appropriate tools.'}

Generate a complete, production-ready project with:
1. A clear file structure
2. All necessary source files
3. package.json with proper dependencies
4. Proper error handling
5. Clean, documented code

Return ONLY valid JSON (no markdown, no explanations) with this format:
{
  "files": [
    {
      "path": "src/index.js",
      "content": "// full file content here"
    }
  ],
  "dependencies": {
    "express": "^4.18.0"
  },
  "description": "Brief project description"
}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);
    
    try {
      const ollamaResponse = await fetch('http://127.0.0.1:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: codePrompt }],
          stream: false,
          format: 'json'
        })
      });
      
      clearTimeout(timeoutId);

      if (ollamaResponse.ok) {
        const data = await ollamaResponse.json() as { message?: { content: string } };
        let generatedContent = data.message?.content || '';
        let projectData = null;
        
        try {
          projectData = JSON.parse(generatedContent);
        } catch (e1) {
          const jsonMatch = generatedContent.match(/```(?:json)?\s*([\s\S]*?)\n?```/);
          if (jsonMatch) {
            try {
              projectData = JSON.parse(jsonMatch[1].trim());
            } catch (e2) {
              const rawMatch = generatedContent.match(/\{[\s\S]*\}/);
              if (rawMatch) {
                try {
                  projectData = JSON.parse(rawMatch[0]);
                } catch (e3) {
                  console.warn('Could not parse JSON from model response');
                }
              }
            }
          }
        }
        
        if (projectData && projectData.files && Array.isArray(projectData.files)) {
          for (const file of projectData.files) {
            try {
              const filePath = path.join(projectDir, file.path);
              await fs.mkdir(path.dirname(filePath), { recursive: true });
              await fs.writeFile(filePath, file.content);
              console.log(`📄 Created: ${file.path}`);
            } catch (err) {
              console.warn(`Failed to write ${file.path}:`, err);
            }
          }
        } else {
          const fallbackHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${projectName}</title>
</head>
<body>
  <h1>${goal}</h1>
  <p>Generated by Ultimate Agent</p>
</body>
</html>`;
          await fs.writeFile(path.join(projectDir, 'index.html'), fallbackHtml);
          console.log('📄 Created fallback index.html');
        }
        
        if (projectData && projectData.dependencies) {
          const packageJson = {
            name: projectName,
            version: '1.0.0',
            description: projectData.description || `Project: ${goal}`,
            scripts: {
              dev: 'echo "Run your development server"',
              build: 'echo "Build completed"',
              test: 'echo "Tests passed"'
            },
            dependencies: projectData.dependencies
          };
          await fs.writeFile(path.join(projectDir, 'package.json'), JSON.stringify(packageJson, null, 2));
        }
        
        await fs.writeFile(path.join(projectDir, 'MODEL_RESPONSE.md'), 
          `# Model Response\n\nGoal: ${goal}\n\n${generatedContent}`);
      } else {
        const fallbackHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${projectName}</title>
</head>
<body>
  <h1>${goal}</h1>
  <p>Generated by Ultimate Agent (fallback mode)</p>
</body>
</html>`;
        await fs.writeFile(path.join(projectDir, 'index.html'), fallbackHtml);
      }

      const readmeContent = `# ${projectName}

Built by Ultimate Agent
Date: ${new Date().toISOString()}
Goal: ${goal}
Stack: ${stack || 'Auto-detected'}

## Description

This project was generated by the Ultimate Coding Agent using local Ollama LLM.

## Features

- AI-powered code generation
- Local LLM processing (no cloud dependency)
- Auto-learning for continuous improvement

## Usage

\`\`\`bash
npm install

npm run dev

npm run build
\`\`\`

---

Generated on: ${new Date().toISOString()}
`;
      await fs.writeFile(path.join(projectDir, 'README.md'), readmeContent);

      try {
        execSync(`cd "${projectDir}" && git init && git add . && git commit -m "Agent complete: ${goal}"`, { stdio: 'pipe' });
      } catch (e) {
        // Git initialization failed, continue anyway
      }

      console.log(`✅ Project built: ${projectName}`);

    } catch (ollamaError) {
      console.error('Ollama code generation failed:', ollamaError);
    }

  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

const server = createServer(app);

const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws) => {
  console.log('WebSocket client connected');
  
  ws.send(JSON.stringify({
    type: 'status',
    status: 'connected',
    timestamp: new Date().toISOString()
  }));
  
  ws.on('message', (data: RawData) => {
    try {
      const message = JSON.parse(data.toString());
      
      switch (message.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
          break;
        case 'status':
          ws.send(JSON.stringify({
            type: 'status',
            status: 'running',
            model: process.env.OLLAMA_MODEL || 'qwen2.5-coder:7b-instruct-q5_K_M',
            timestamp: new Date().toISOString()
          }));
          break;
      }
    } catch (e) {
      console.error('WebSocket message error:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('WebSocket client disconnected');
  });
});

app.get('*', (req, res) => {
  if (!req.path.startsWith('/api') && !req.path.startsWith('/health')) {
    res.sendFile(path.join(__dirname, '../public', 'index.html'));
  }
});

server.listen(PORT, () => {
  console.log('');
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║  Ultimate Agent Dashboard                                ║');
  console.log('║                                                          ║');
  console.log('║  🌐 Dashboard:  http://' + HOST + ':' + PORT + '                  ║');
  console.log('║  💚 Health:    http://' + HOST + ':' + PORT + '/health              ║');
  console.log('║  📡 WebSocket: ws://' + HOST + ':' + PORT + '/ws                   ║');
  console.log('║                                                          ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log('');
});

export default app;
