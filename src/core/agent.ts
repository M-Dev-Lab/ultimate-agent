import { OllamaQwenTool, QwenTask } from '../tools/ollamaQwenTool';
import { TelegramChannel } from '../channels/telegram';
import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import { execSync } from 'child_process';

interface AgentMessage {
  channel: 'telegram';
  sender: string;
  content: string;
  timestamp: number;
  messageId: string;
  metadata?: any;
}

interface AgentResponse {
  content: string;
  channel: string;
  recipient: string;
}

interface AgentMessage {
  channel: 'telegram';
  sender: string;
  content: string;
  timestamp: number;
  messageId: string;
  metadata?: any;
}

interface AgentResponse {
  content: string;
  channel: string;
  recipient: string;
}

interface ProjectResult {
  success: boolean;
  path?: string;
  summary: string;
}

export class Agent extends EventEmitter {
  private qwenTool: OllamaQwenTool;
  private channels: {
    telegram?: TelegramChannel;
  } = {};
  private activeTasks: Map<string, any> = new Map();
  private workspaces: Map<string, string> = new Map();
  private outputsDir: string;

  constructor() {
    super();
    this.qwenTool = new OllamaQwenTool();
    this.outputsDir = path.join(process.cwd(), 'outputs');
  }

  async initialize(): Promise<void> {
    try {
      console.log('🚀 Initializing Ultimate Agent...');
      
      // Initialize messaging channels
      await this.initializeChannels();
      
      // Setup event listeners
      this.setupChannelListeners();
      
      // Initialize workspaces
      await this.initializeWorkspaces();
      
      // Log model info
      console.log(`🧠 Model: ${this.qwenTool.getModel()}`);
      
      console.log('✅ Ultimate Agent initialized successfully');
    } catch (error: any) {
      console.error('Failed to initialize agent:', error);
      throw error;
    }
  }

  private async initializeChannels(): Promise<void> {
    try {
      // Initialize Telegram only
      this.channels.telegram = new TelegramChannel();
      this.channels.telegram.setAgent(this);
      await this.channels.telegram.initialize();

      console.log('📱 Telegram channel initialized');
    } catch (error: any) {
      console.warn('Failed to initialize Telegram channel:', error.message);
    }
  }

  private setupChannelListeners(): void {
    Object.values(this.channels).forEach(channel => {
      if (channel) {
        channel.on('message', (message: AgentMessage) => {
          this.handleMessage(message);
        });
      }
    });
  }

  private async initializeWorkspaces(): Promise<void> {
    // Create default workspace
    const defaultWorkspace = './workspaces/current';
    try {
      await fs.mkdir(defaultWorkspace, { recursive: true });
      this.workspaces.set('current', defaultWorkspace);
      this.qwenTool.setWorkspace(defaultWorkspace);
    } catch (error) {
      console.warn('Workspace initialization warning:', error);
    }
  }

  async handleMessage(message: AgentMessage): Promise<void> {
    try {
      console.log(`🧠 Processing ${message.channel} message:`, message.content.substring(0, 100));
      
      // Store message
      await this.logMessage(message);
      
      // Check if this is a system command or development request
      const response = await this.processMessage(message);
      
      // Send response through appropriate channel
      await this.sendResponse(response, message.channel);
      
    } catch (error: any) {
      console.error('Error handling message:', error);
      
      const errorResponse: AgentResponse = {
        content: `❌ Error processing your request: ${error.message}`,
        channel: message.channel,
        recipient: message.sender
      };
      
      await this.sendResponse(errorResponse, message.channel);
    }
  }
  
  // New method for chatty interactions
  async sendChattyMessage(message: AgentMessage, context?: string): Promise<void> {
    try {
      // Generate a chatty response using Qwen
      const prompt = `You are a friendly and helpful AI coding assistant. The user has sent a message: "${message.content}"
      
      ${context ? `Context: ${context}` : ''}
      
      Respond in a conversational, helpful manner. Be brief but informative. If they're asking for help with coding, 
      provide guidance or offer to build something specific. If they're just saying hello, respond warmly.
      
      Keep your response under 200 words.`;
      
      const qwenResponse = await this.qwenTool.complete(prompt, { temperature: 0.7, maxTokens: 500 });
      
      const response: AgentResponse = {
        content: qwenResponse.content || "I'm here to help! What would you like to work on today?",
        channel: message.channel,
        recipient: message.sender
      };
      
      await this.sendResponse(response, message.channel);
    } catch (error: any) {
      console.error('Error sending chatty message:', error);
      
      const errorResponse: AgentResponse = {
        content: "I'm a bit confused right now. Could you rephrase that?",
        channel: message.channel,
        recipient: message.sender
      };
      
      await this.sendResponse(errorResponse, message.channel);
    }
  }

  private async processMessage(message: AgentMessage): Promise<AgentResponse> {
    const content = message.content.toLowerCase().trim();
    
    // System commands
    if (content.startsWith('status')) {
      return await this.handleStatusCommand(message);
    }
    
    if (content.startsWith('workspace ')) {
      return await this.handleWorkspaceCommand(content, message);
    }
    
    if (content.startsWith('agent ')) {
      return await this.handleAgentCommand(content, message);
    }
    
    if (content.startsWith('test ')) {
      return await this.handleTestCommand(content, message);
    }
    
    if (content.startsWith('help')) {
      return this.handleHelpCommand(message);
    }
    
    // Default: Use Qwen for coding request
    return await this.handleQwenRequest(message);
  }

  private async handleStatusCommand(message: AgentMessage): Promise<AgentResponse> {
    const rateLimit = await this.qwenTool.checkRateLimit();
    const workspace = this.qwenTool.getWorkspace();
    
    return {
      content: `🤖 **Ultimate Agent + Qwen Status**

📊 **Rate Limits**: ${rateLimit.requestsUsed}/${rateLimit.requestsRemaining + rateLimit.requestsUsed} requests today
🔄 **Reset Time**: ${new Date(rateLimit.resetTime || 0).toLocaleString()}
💾 **Current Workspace**: ${workspace}
🧠 **AI Model**: ${this.qwenTool.getModel()}
📱 **Channels**: Telegram ${this.channels.telegram?.isRunning() ? '✅' : '❌'}

**Active Tasks**: ${this.activeTasks.size}
**Powered by**: OpenCode + Qwen3-Coder-Plus (2k free requests/day)`,
      channel: message.channel,
      recipient: message.sender
    };
  }

  private async handleWorkspaceCommand(content: string, message: AgentMessage): Promise<AgentResponse> {
    const parts = content.split(' ');
    const action = parts[1];
    
    switch (action) {
      case 'create':
        const workspaceName = parts[2];
        if (!workspaceName) {
          return {
            content: '❌ Please provide a workspace name: `workspace create <name>`',
            channel: message.channel,
            recipient: message.sender
          };
        }
        
        const newWorkspace = `./workspaces/${workspaceName}`;
        await require('fs').promises.mkdir(newWorkspace, { recursive: true });
        this.workspaces.set(workspaceName, newWorkspace);
        
        return {
          content: `✅ Workspace "${workspaceName}" created at ${newWorkspace}`,
          channel: message.channel,
          recipient: message.sender
        };
        
      case 'list':
        const workspaces = Array.from(this.workspaces.keys());
        return {
          content: `📁 Available workspaces:\n${workspaces.map(w => `• ${w}`).join('\n')}`,
          channel: message.channel,
          recipient: message.sender
        };
        
      case 'switch':
        const targetWorkspace = parts[2];
        if (!targetWorkspace || !this.workspaces.has(targetWorkspace)) {
          return {
            content: '❌ Invalid workspace. Use `workspace list` to see available workspaces.',
            channel: message.channel,
            recipient: message.sender
          };
        }
        
        this.qwenTool.setWorkspace(this.workspaces.get(targetWorkspace)!);
        return {
          content: `✅ Switched to workspace: ${targetWorkspace}`,
          channel: message.channel,
          recipient: message.sender
        };
        
      default:
        return {
          content: '❓ Unknown workspace command. Available: create, list, switch',
          channel: message.channel,
          recipient: message.sender
        };
    }
  }

  private async handleAgentCommand(content: string, message: AgentMessage): Promise<AgentResponse> {
    const parts = content.split(' ');
    const agentName = parts[1];
    const task = parts.slice(2).join(' ');
    
    if (!agentName || !task) {
      return {
        content: '❌ Usage: `agent <agent-name> <task>`\n\nAvailable agents: frontend-agent, backend-agent, mobile-agent, tester, deployer',
        channel: message.channel,
        recipient: message.sender
      };
    }
    
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const qwenTask: QwenTask = {
      id: taskId,
      type: this.getTaskType(task),
      agent: agentName,
      goal: task,
      files: [],
      dependencies: [],
      status: 'pending'
    };

    this.activeTasks.set(taskId, qwenTask);
    
    try {
      const result = await this.qwenTool.executeAgent(agentName, qwenTask);
      (qwenTask as QwenTask).status = result.success ? 'completed' : 'failed';
      
      const status = result.success ? '✅' : '❌';
      return {
        content: `${status} **Agent: ${agentName}**\n\n**Task**: ${task}\n\n${result.success ? result.data.output : '❌ ' + result.error}\n\n⏱️ Execution time: ${result.executionTime}ms`,
        channel: message.channel,
        recipient: message.sender
      };
    } catch (error: any) {
      qwenTask.status = 'failed';
      return {
        content: `❌ **Agent: ${agentName}** failed\n\n**Error**: ${error.message}`,
        channel: message.channel,
        recipient: message.sender
      };
    }
  }

  private getTaskType(task: string): QwenTask['type'] {
    const lowerTask = task.toLowerCase();
    if (lowerTask.includes('react') || lowerTask.includes('frontend') || lowerTask.includes('ui')) {
      return 'frontend';
    }
    if (lowerTask.includes('api') || lowerTask.includes('backend') || lowerTask.includes('server')) {
      return 'backend';
    }
    if (lowerTask.includes('mobile') || lowerTask.includes('app') || lowerTask.includes('ios') || lowerTask.includes('android')) {
      return 'mobile';
    }
    if (lowerTask.includes('test') || lowerTask.includes('qa')) {
      return 'testing';
    }
    if (lowerTask.includes('deploy') || lowerTask.includes('production') || lowerTask.includes('ci/cd')) {
      return 'deployment';
    }
    return 'backend'; // default
  }

  private async handleTestCommand(content: string, message: AgentMessage): Promise<AgentResponse> {
    const commands = content.substring(5).trim().split(' ') || ['npm test'];
    const workspace = this.qwenTool.getWorkspace();
    
    try {
      const result = await this.qwenTool.testRun(commands);
      const status = result.passed ? '✅' : '❌';
      
      return {
        content: `${status} **Test Results**\n\n**Commands**: ${commands.join(', ')}\n\n**Output**:\n${result.output}\n\n${result.errors && result.errors.length > 0 ? '**Errors**:\n' + result.errors.join('\n') : ''}`,
        channel: message.channel,
        recipient: message.sender
      };
    } catch (error: any) {
      return {
        content: `❌ Test execution failed: ${error.message}`,
        channel: message.channel,
        recipient: message.sender
      };
    }
  }

  private async handleHelpCommand(message: AgentMessage): Promise<AgentResponse> {
    return {
      content: `🤖 **Ultimate Agent + Qwen Help**

**Available Commands:**
• \`status\` - Show system status and rate limits
• \`workspace create <name>\` - Create new workspace
• \`workspace list\` - List all workspaces
• \`workspace switch <name>\` - Switch to workspace
• \`agent <agent-name> <task>\` - Execute specific agent task
• \`test <commands>\` - Run tests (default: npm test)
• \`<coding request>\` - Natural language coding request

**Available Agents:**
• \`frontend-agent\` - React, Next.js, TypeScript, Tailwind
• \`backend-agent\` - Node.js, APIs, databases
• \`mobile-agent\` - React Native, Flutter
• \`tester\` - Testing and QA
• \`deployer\` - Deployment and DevOps

**AI Model:** Qwen3-Coder-Plus (2k free requests/day)
**Powered by:** OpenCode + Qwen

**Examples:**
• \`agent frontend-agent Create React login component\`
• \`agent backend-agent Build Express API with MongoDB\`
• \`test npm run test && npm run coverage\`
• \`Build a complete e-commerce site with React and Node.js\``,
      channel: message.channel,
      recipient: message.sender
    };
  }

  private async handleQwenRequest(message: AgentMessage): Promise<AgentResponse> {
    try {
      // Use Qwen to plan and execute
      const plan = await this.qwenTool.planEdits(message.content);

      const response = `🧠 **Qwen Development Plan**

**Goal**: ${plan.goal}

**Planned Tasks** (${plan.tasks.length}):
${plan.tasks.map((task: any, i: number) =>
  `${i + 1}. **${task.agent}** (${task.type})
   ${task.goal}
   Files: ${task.files && task.files.length > 0 ? task.files.join(', ') : 'To be determined'}
 `).join('\n')}

**Estimated Time**: ${plan.estimatedTime} minutes
**AI Model**: ${plan.model}

🔄 *Executing tasks now...*`;

      // Execute tasks in parallel
      const results = await Promise.allSettled(
        plan.tasks.map((task: any) => this.qwenTool.executeAgent(task.agent, task))
      );

      const successful = results.filter((r: any) => r.status === 'fulfilled' && r.value.success);
      const failed = results.filter((r: any) => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success));

      return {
        content: response + `\n\n✅ **Completed**: ${successful.length} tasks\n${failed.length > 0 ? '❌ **Failed**: ' + failed.length + ' tasks' : ''}`,
        channel: message.channel,
        recipient: message.sender
      };
    } catch (error: any) {
      return {
        content: `❌ Qwen processing failed: ${error.message}`,
        channel: message.channel,
        recipient: message.sender
      };
    }
  }

  private async sendResponse(response: AgentResponse, channel: string): Promise<void> {
    try {
      switch (channel) {
        case 'telegram':
          await this.channels.telegram?.sendMessage(response);
          break;
      }
    } catch (error: any) {
      console.error('Error sending response:', error);
    }
  }

  private async logMessage(message: AgentMessage): Promise<void> {
    const logEntry = {
      timestamp: new Date().toISOString(),
      channel: message.channel,
      sender: message.sender,
      content: message.content.substring(0, 200),
      messageId: message.messageId
    };

    // Simple logging - in production this would use the memory system
    console.log('📝 Message logged:', logEntry);
  }

  async buildProject(goal: string, workspace: string): Promise<ProjectResult> {
    try {
      // Ensure outputs directory exists
      await fs.mkdir(this.outputsDir, { recursive: true });

      // Create workspace if it doesn't exist
      const workspacePath = path.join(process.cwd(), 'workspaces', workspace);
      await fs.mkdir(workspacePath, { recursive: true });

      // Use Qwen to plan and execute
      const plan = await this.qwenTool.planEdits(goal);

      // Execute tasks in parallel
      const results = await Promise.allSettled(
        plan.tasks.map((task: any) => this.qwenTool.executeAgent(task.agent, task))
      );

      const successful = results.filter((r: any) => r.status === 'fulfilled' && r.value.success);
      const failed = results.filter((r: any) => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success));

      // Archive to outputs/ on success
      if (successful.length > 0 && failed.length === 0) {
        const projectName = `${goal.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now()}`;
        const outputPath = path.join(this.outputsDir, projectName);

        await execSync(`cp -r ${workspacePath} ${outputPath}`, { stdio: 'pipe' });
        await execSync(`cd ${outputPath} && git init && git add . && git commit -m "Agent complete: ${goal}"`, { stdio: 'pipe' });

        return {
          success: true,
          path: outputPath,
          summary: `✅ *Build Complete*\n\n**Project**: ${goal}\n**Path**: ${outputPath}\n**Tasks**: ${successful.length} completed\n\nArchived to outputs/ folder with git init.`
        };
      }

      return {
        success: false,
        summary: `❌ *Build Failed*\n\n**Project**: ${goal}\n**Completed**: ${successful.length} tasks\n**Failed**: ${failed.length} tasks`
      };
    } catch (error: any) {
      return {
        success: false,
        summary: `❌ Build failed: ${error.message}`
      };
    }
  }

  async getStatus(): Promise<string> {
    try {
      const projects = await this.listProjects();
      const workspace = this.qwenTool.getWorkspace();
      const activeTasks = this.activeTasks.size;

      return `📊 *Ultimate Agent Status*\n\n` +
        `🏢 **AI Model**: ${this.qwenTool.getModel()}\n` +
        `💾 **Current Workspace**: ${workspace}\n` +
        `📱 **Telegram**: ${this.channels.telegram?.isRunning() ? '✅ Online' : '❌ Offline'}\n` +
        `🔧 **Active Tasks**: ${activeTasks}\n\n` +
        `📁 **Completed Projects**:\n${projects}`;
    } catch (error: any) {
      return `❌ Error getting status: ${error.message}`;
    }
  }

  async listProjects(): Promise<string> {
    try {
      await fs.mkdir(this.outputsDir, { recursive: true });
      const entries = await fs.readdir(this.outputsDir, { withFileTypes: true });

      const projects = entries
        .filter(entry => entry.isDirectory())
        .map(dir => {
          const projectPath = path.join(this.outputsDir, dir.name);
          return { name: dir.name, path: projectPath };
        });

      if (projects.length === 0) {
        return '• No projects completed yet\n\nUse /build to create your first project!';
      }

      return projects.map(p => `• ${p.name}`).join('\n');
    } catch (error: any) {
      return '• Unable to list projects\n\n' + error.message;
    }
  }

  async shutdown(): Promise<void> {
    console.log('🔄 Shutting down Ultimate Agent...');

    try {
      await this.channels.telegram?.stop();

      console.log('✅ Ultimate Agent shutdown complete');
    } catch (error: any) {
      console.error('Error during shutdown:', error);
    }
  }

  getActiveTasksCount(): number {
    return this.activeTasks.size;
  }
}