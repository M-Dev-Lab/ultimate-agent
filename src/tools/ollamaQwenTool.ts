import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs/promises';
import * as path from 'path';
import ollama from 'ollama';
import * as fsSync from 'fs';

const execAsync = promisify(exec);

export interface QwenTask {
  id: string;
  type: 'frontend' | 'backend' | 'mobile' | 'testing' | 'deployment';
  agent: string;
  goal: string;
  files: string[];
  dependencies: string[];
  status: 'pending' | 'completed' | 'failed';
}

export interface QwenPatchPlan {
  goal: string;
  tasks: QwenTask[];
  estimatedTime: number;
  model: string;
}

export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
  executionTime: number;
}

export interface LearningEntry {
  id: string;
  timestamp: number;
  prompt: string;
  response: string;
  rating: number;
  tags: string[];
}

export class OllamaQwenTool {
  private ollama: any;
  private workspace: string;
  private model!: string;
  private learningData: Map<string, LearningEntry[]>;
  private learningFile: string;

  constructor(workspace: string = './workspaces/current') {
    this.workspace = workspace;
    this.ollama = ollama;
    this.learningData = new Map();
    this.learningFile = path.join(process.cwd(), 'data', 'learning-data.json');
    this.loadLearningData();
    this.initializeModel();
  }

  private async initializeModel(): Promise<void> {
    try {
      // Check for Claude API first
      const claudeApiKey = process.env.CLAUDE_API_KEY;
      if (claudeApiKey) {
        this.model = 'claude-api:primary';
        console.log(`✅ Using model: ${this.model} (Claude API)`);
        return;
      }

      // Fallback to checking environment variable for Qwen3-code cloud
      const qwenCloud = process.env.QWEN3_CODE_CLOUD;
      if (qwenCloud) {
        this.model = 'qwen3-coder:cloud';
        console.log(`✅ Using model: ${this.model} (Qwen3 Cloud)`);
        return;
      }

      // Then try local models
      const models = await this.listModels();
      
      if (models.length === 0) {
        console.warn('⚠️ No Ollama models found. Please pull a model first.');
        this.model = 'qwen2.5-coder:7b';
        return;
      }

      const modelNames = models.map((m: any) => m.name || m);
      console.log(`📦 Found ${modelNames.length} local models: ${modelNames.join(', ')}`);

      // Priority order - prefer Qwen models first, then other code models
      const preferredModels = [
        'qwen3-coder',
        'qwen2.5-coder',
        'codellama',
        'llama2-uncensored',
        'neural-chat',
        'llava:7b'
      ];

      // Find first available preferred model
      let selectedModel: string | null = null;
      
      for (const pattern of preferredModels) {
        const match = modelNames.find((name: string) => 
          name.toLowerCase().includes(pattern.toLowerCase())
        );
        if (match) {
          selectedModel = match;
          break;
        }
      }

      // Fallback to first available model
      if (!selectedModel && modelNames.length > 0) {
        selectedModel = modelNames[0];
      }

      if (selectedModel) {
        this.model = selectedModel;
        console.log(`✅ Using model: ${this.model}`);
      } else {
        this.model = 'qwen2.5-coder:7b';
      }
    } catch (error) {
      console.warn('⚠️ Failed to detect models, using default:', error);
      this.model = 'qwen2.5-coder:7b';
    }
  }

  async planEdits(goal: string, context?: string): Promise<QwenPatchPlan> {
    try {
      const prompt = `You are a lead planner agent for Ultimate Agent. Decompose this goal into specific subtasks for different agents.

Goal: ${goal}

Context: ${context || 'No additional context provided'}

Break down into specific tasks for:
- Frontend development (React, Next.js, Vue, etc.)
- Backend development (Node.js, APIs, databases)
- Mobile development (React Native, Flutter)
- Testing and QA
- Deployment and DevOps

Return JSON:
{
  "goal": "original goal",
  "tasks": [
    {
      "id": "task_id",
      "type": "frontend|backend|mobile|testing|deployment",
      "agent": "frontend-agent|backend-agent|mobile-agent|tester|deployer",
      "goal": "specific task goal",
      "files": ["file1.js", "file2.ts"],
      "dependencies": ["task_id1", "task_id2"],
      "status": "pending"
    }
  ],
  "estimatedTime": 15,
  "model": "${this.model}"
}`;

      const response = await this.chatWithOllama(prompt, 0.3, 4000);

      const content = response || '';
      const parsed = this.extractJSON(content);

      this.storeInteraction(prompt, content, 'planning', ['task-planning', 'decomposition']);

      return parsed;
    } catch (error: any) {
      throw new Error(`Ollama planning failed: ${error.message}`);
    }
  }

  async executeAgent(agentName: string, task: QwenTask): Promise<ToolResult> {
    const startTime = Date.now();

    try {
      const agentPrompt = this.getAgentPrompt(agentName);
      const taskPrompt = `${agentPrompt}

Execute this task:
${task.goal}

Files to modify: ${task.files.join(', ')}

Focus on clean, production-ready code with proper error handling.`;

      const response = await this.chatWithOllama(taskPrompt, 0.2, 8000);

      this.storeInteraction(taskPrompt, response || '', 'execution', ['agent-execution', agentName, task.type]);

      const changes = await this.parseAndApplyChanges(response || '', task.files);

      return {
        success: true,
        data: {
          changes,
          output: response || '',
          agent: agentName,
          task: task.id
        },
        executionTime: Date.now() - startTime
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message,
        executionTime: Date.now() - startTime
      };
    }
  }

  private getAgentPrompt(agentName: string): string {
    const prompts = {
      'frontend-agent': 'You are an expert frontend developer specializing in React, Next.js, TypeScript, and Tailwind CSS. Write modern, responsive, and performant code.',
      'backend-agent': 'You are an expert backend developer specializing in Node.js, Express, APIs, databases, and cloud services.',
      'mobile-agent': 'You are an expert mobile developer specializing in React Native and Flutter for iOS and Android.',
      'tester': 'You are a QA engineer specializing in testing, debugging, and ensuring code quality.',
      'deployer': 'You are a DevOps engineer specializing in deployment, CI/CD, and infrastructure management.'
    };
    return prompts[agentName as keyof typeof prompts] || 'You are a helpful software developer.';
  }

  private async parseAndApplyChanges(response: string, files: string[]): Promise<any[]> {
    const changes = [];

    for (const file of files) {
      try {
        const filePath = path.join(this.workspace, file);
        await fs.mkdir(path.dirname(filePath), { recursive: true });

        const codeMatch = response.match(/```[\w]*\n([\s\S]*?)\n```/);
        const code = codeMatch ? codeMatch[1] : `// Generated code for ${file}\n${response}`;

        await fs.writeFile(filePath, code);
        changes.push({ file, action: 'created/modified', lines: code.split('\n').length });
      } catch (error) {
        changes.push({ file, action: 'error', error: (error as Error).message });
      }
    }

    return changes;
  }

  async testRun(commands: string[]): Promise<any> {
    try {
      const results = [];

      for (const command of commands) {
        try {
          const { stdout, stderr } = await execAsync(`cd ${this.workspace} && ${command}`, { timeout: 30000 });
          results.push({
            command,
            success: !stderr,
            output: stdout,
            error: stderr
          });
        } catch (error: any) {
          results.push({
            command,
            success: false,
            error: error.message
          });
        }
      }

      return {
        passed: results.every(r => r.success),
        output: results.map(r => r.output).join('\n'),
        errors: results.filter(r => !r.success).map(r => r.error),
        results
      };
    } catch (error: any) {
      return {
        passed: false,
        output: '',
        errors: [error.message],
        results: []
      };
    }
  }

  async analyzeRepo(): Promise<string> {
    try {
      const { stdout } = await execAsync(`cd ${this.workspace} && find . -name "*.ts" -o -name "*.js" -o -name "*.json" | head -20`);
      return `Repository analysis:\n${stdout}`;
    } catch (error: any) {
      throw new Error(`Repository analysis failed: ${error.message}`);
    }
  }

  public async chatWithOllama(prompt: string, temperature: number = 0.7, maxTokens: number = 4096): Promise<string> {
    try {
      const response = await this.ollama.chat({
        model: this.model,
        messages: [{ role: 'user', content: prompt }],
        options: {
          temperature,
          num_predict: maxTokens,
          top_p: 0.9,
          top_k: 40
        },
        stream: false,
        format: 'json'  // Force JSON output
      });

      return response.message?.content || '';
    } catch (error: any) {
      throw new Error(`Ollama chat failed: ${error.message}`);
    }
  }

  private extractJSON(content: string): any {
    try {
      // Try direct parse first
      return JSON.parse(content);
    } catch (e) {
      // Try to extract from markdown code blocks
      const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)\n?```/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[1].trim());
        } catch (e2) {
          // Try to find raw JSON object in text
          const rawMatch = content.match(/\{[\s\S]*\}/);
          if (rawMatch) {
            try {
              return JSON.parse(rawMatch[0]);
            } catch (e3) {
              throw new Error(`Invalid JSON: ${rawMatch[0].substring(0, 100)}...`);
            }
          }
        }
      }
      
      // Last resort: try to find JSON in content
      const lastBrace = content.lastIndexOf('{');
      if (lastBrace >= 0) {
        try {
          return JSON.parse(content.substring(lastBrace));
        } catch (e) {
          throw new Error(`Could not parse JSON from response`);
        }
      }
      
      throw new Error(`Invalid JSON response: ${content.substring(0, 100)}`);
    }
  }

  async checkRateLimit(): Promise<{ requestsUsed: number; requestsRemaining: number; resetTime: number | null }> {
    return {
      requestsUsed: 0,
      requestsRemaining: Infinity,
      resetTime: null
    };
  }

  setWorkspace(workspace: string) {
    this.workspace = workspace;
  }

  getWorkspace(): string {
    return this.workspace;
  }

  getModel(): string {
    return this.model;
  }

  setModel(model: string) {
    this.model = model;
  }

  async pullModel(model: string): Promise<void> {
    try {
      console.log(`📥 Pulling model ${model}...`);
      const response = await this.ollama.pull({ model, stream: true });
      
      for await (const chunk of response) {
        if (chunk.total && chunk.completed) {
          const percent = ((chunk.completed / chunk.total) * 100).toFixed(2);
          process.stdout.write(`\r📥 Downloading: ${percent}%`);
        }
      }
      process.stdout.write('\n');
      
      console.log(`✅ Model ${model} pulled successfully`);
    } catch (error: any) {
      throw new Error(`Failed to pull model: ${error.message}`);
    }
  }

  async listModels(): Promise<any[]> {
    try {
      const response = await this.ollama.list();
      return response.models || [];
    } catch (error: any) {
      console.error('Failed to list models:', error);
      return [];
    }
  }

  private loadLearningData(): void {
    try {
      if (fsSync.existsSync(this.learningFile)) {
        const data = fsSync.readFileSync(this.learningFile, 'utf-8');
        const entries = JSON.parse(data) as LearningEntry[];
        entries.forEach(entry => {
          const key = `${entry.tags.join('-')}-${Math.floor(entry.timestamp / 86400000)}`;
          if (!this.learningData.has(key)) {
            this.learningData.set(key, []);
          }
          this.learningData.get(key)!.push(entry);
        });
        console.log(`📚 Loaded ${entries.length} learning entries`);
      }
    } catch (error) {
      console.warn('Failed to load learning data:', error);
    }
  }

  private async saveLearningData(): Promise<void> {
    try {
      await fs.mkdir(path.dirname(this.learningFile), { recursive: true });

      const allEntries: LearningEntry[] = [];
      this.learningData.forEach(entries => {
        allEntries.push(...entries);
      });

      await fs.writeFile(this.learningFile, JSON.stringify(allEntries, null, 2));
      console.log(`💾 Saved ${allEntries.length} learning entries`);
    } catch (error) {
      console.error('Failed to save learning data:', error);
    }
  }

  private storeInteraction(prompt: string, response: string, rating: string, tags: string[]): void {
    const entry: LearningEntry = {
      id: `entry-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      prompt: prompt.substring(0, 5000),
      response: response.substring(0, 10000),
      rating: 5,
      tags
    };

    const key = `${tags.join('-')}-${Math.floor(Date.now() / 86400000)}`;
    if (!this.learningData.has(key)) {
      this.learningData.set(key, []);
    }
    this.learningData.get(key)!.push(entry);

    this.saveLearningData();
  }

  async rateInteraction(entryId: string, rating: number): Promise<void> {
    const allEntries = Array.from(this.learningData.values());
    for (const entries of allEntries) {
      const entry = entries.find(e => e.id === entryId);
      if (entry) {
        entry.rating = rating;
        await this.saveLearningData();
        console.log(`⭐ Rated interaction ${entryId}: ${rating}/5`);
        return;
      }
    }
  }

  async exportForFineTuning(outputPathParam?: string): Promise<string> {
    try {
      const outputPath = outputPathParam || path.join(process.cwd(), 'data', 'fine-tuning-data.jsonl');

      const allEntries: LearningEntry[] = [];
      this.learningData.forEach(entries => {
        allEntries.push(...entries.filter(e => e.rating >= 4));
      });

      if (allEntries.length === 0) {
        throw new Error('No high-quality entries found for fine-tuning (need rating >= 4)');
      }

      const jsonlLines = allEntries.map(entry => {
        return JSON.stringify({
          prompt: entry.prompt,
          completion: entry.response,
          tags: entry.tags
        });
      });

      await fs.mkdir(path.dirname(outputPath), { recursive: true });
      await fs.writeFile(outputPath, jsonlLines.join('\n'));

      console.log(`📦 Exported ${allEntries.length} entries to ${outputPath}`);
      console.log(`💡 Use this file with Unsloth, Hugging Face, or Ollama for fine-tuning`);

      return outputPath;
    } catch (error: any) {
      throw new Error(`Failed to export fine-tuning data: ${error.message}`);
    }
  }

  getLearningStats(): { totalEntries: number; averageRating: number; byTag: Record<string, number> } {
    const allEntries: LearningEntry[] = [];
    this.learningData.forEach(entries => {
      allEntries.push(...entries);
    });

    const totalEntries = allEntries.length;
    const averageRating = totalEntries > 0
      ? allEntries.reduce((sum, e) => sum + e.rating, 0) / totalEntries
      : 0;

    const byTag: Record<string, number> = {};
    allEntries.forEach(entry => {
      entry.tags.forEach(tag => {
        byTag[tag] = (byTag[tag] || 0) + 1;
      });
    });

    return { totalEntries, averageRating, byTag };
  }

  async autoFineTune(): Promise<void> {
    try {
      console.log('🔄 Auto-fine-tuning analysis...');

      const stats = this.getLearningStats();
      console.log(`📊 Learning stats: ${stats.totalEntries} entries, avg rating: ${stats.averageRating.toFixed(2)}/5`);

      if (stats.totalEntries < 10) {
        console.log('⚠️ Not enough data for fine-tuning (need at least 10 high-rated entries)');
        return;
      }

      const exportPath = await this.exportForFineTuning();

      console.log('🎯 Fine-tuning data ready!');
      console.log(`📁 Export file: ${exportPath}`);
      console.log('');
      console.log('Next steps for fine-tuning:');
      console.log('1. Use Unsloth for efficient training: https://github.com/unslothai/unsloth');
      console.log('2. Or use Ollama with Modelfile for custom fine-tuning');
      console.log('3. Upload to Hugging Face for easier model management');
      console.log('');
      console.log('💡 Tip: Rate your interactions with higher ratings (4-5) for better fine-tuning data');
    } catch (error: any) {
      console.error('Auto-fine-tuning failed:', error.message);
    }
  }
}
