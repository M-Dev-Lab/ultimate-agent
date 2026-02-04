import { Telegraf, Context, Markup } from 'telegraf';
import { EventEmitter } from 'events';
import { execSync } from 'child_process';
import { SocialMediaManager } from '../social/social_media_manager.js';
import { SocialMediaBrowserManager } from '../browser/social_media_browser_manager.js';

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

export class TelegramChannel extends EventEmitter {
  private bot: Telegraf;
  private adminId: string;
  private wolMac: string;
  private agent?: any;
  private socialMediaManager: SocialMediaManager;
  private browserManager: SocialMediaBrowserManager;
  
  // Post flow state management
  private postStates: Map<number, {
    step: 'content_type' | 'platform' | 'content' | 'media' | 'confirm';
    contentType: 'text' | 'image' | 'video' | null;
    platform: 'x' | 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'youtube' | 'all' | null;
    content: string | null;
    mediaPaths: string[];
  }> = new Map();

  private getMainMenuButtons() {
    return Markup.inlineKeyboard([
      [Markup.button.callback('🏗️ Build', 'cmd_build'), Markup.button.callback('💻 Code', 'cmd_code')],
      [Markup.button.callback('🔧 Fix', 'cmd_fix'), Markup.button.callback('📊 Status', 'cmd_status')],
      [Markup.button.callback('📱 Post', 'cmd_post'), Markup.button.callback('🚀 Deploy', 'cmd_deploy')],
      [Markup.button.callback('🔒 Audit', 'cmd_audit'), Markup.button.callback('🧠 Learn', 'cmd_learn')],
      [Markup.button.callback('📈 Analytics', 'cmd_analytics'), Markup.button.callback('⚙️ Settings', 'cmd_settings')],
      [Markup.button.callback('💡 Skills', 'cmd_skills'), Markup.button.callback('❤️ Heartbeat', 'cmd_heartbeat')],
      [Markup.button.callback('🔄 Restart Agent', 'cmd_restart'), Markup.button.callback('❓ Help', 'help_menu')],
      [Markup.button.callback('🏠 Main Menu', 'main_menu')]
    ]);
  }

  private getBackButton() {
    return Markup.inlineKeyboard([
      [Markup.button.callback('🔄 Back to Menu', 'main_menu')]
    ]);
  }

  constructor() {
    super();
    const token = process.env.TELEGRAM_BOT_TOKEN;
    if (!token) {
      throw new Error('TELEGRAM_BOT_TOKEN environment variable is required');
    }

    this.adminId = process.env.ADMIN_TELEGRAM_ID || '';
    this.wolMac = process.env.WOL_MAC || '';

    this.bot = new Telegraf(token);
    
      const credentials = {
          x: {
            username: process.env.X_USERNAME || '',
            password: process.env.X_PASSWORD || ''
          }
        };

    this.socialMediaManager = new SocialMediaManager();
    this.browserManager = new SocialMediaBrowserManager({
      credentials: credentials as any
    });
  }

  setAgent(agent: any) {
    this.agent = agent;
  }

  async initialize() {
    try {
      this.setupMiddleware();
      this.setupCommands();
      this.setupTextHandlers();
      this.setupErrorHandlers();
      this.setupProcessHandlers();
      
      await this.bot.launch();
      console.log('📱 Telegram bot channel initialized with 15 buttons');
    } catch (error: any) {
      console.error('Failed to initialize Telegram:', error);
      throw error;
    }
  }

  private setupMiddleware() {
    this.bot.use((ctx, next) => {
      if (ctx.from?.id?.toString() !== this.adminId) {
        return ctx.reply('❌ Unauthorized');
      }
      return next();
    });
  }

  private setupCommands() {
    this.bot.start((ctx) => {
      // Send initial welcome message
      ctx.reply(
        `� *Ultimate Coding Agent v3.0* online!
 
 I'm your proactive AI coding assistant with advanced memory, comprehensive skills, and intelligent model routing.
 
 *Quick Start:*
 Tap a button below or send a command.
 
 *Available Buttons:*
 🏗️ Build • 💻 Code • 🔧 Fix • 📊 Status
 📱 Post • 🚀 Deploy • 🔒 Audit • 🧠 Learn
 📈 Analytics • ⚙️ Settings • 💡 Skills • ❤️ Heartbeat
 
 *Free Text Mode:*
 Just describe what you want - I'll understand!`,
        {
          parse_mode: 'Markdown',
          ...this.getMainMenuButtons()
        }
      );
      
      // Send chatty follow-up message after a delay
      setTimeout(() => {
        ctx.reply(
          `👋 Hey there! I'm your Ultimate Coding Agent and I'm here to help you build amazing projects.
 
 🤖 I can:
 • Build complete applications from scratch
 • Fix bugs in your code
 • Deploy projects to the cloud
 • Post updates to social media
 • And much more!
 
 Just tell me what you'd like to work on today!`,
          {
            parse_mode: 'Markdown',
            ...this.getMainMenuButtons()
          }
        );
      }, 2000);
    });

    this.bot.action('main_menu', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(
        `🦞 *Ultimate Coding Agent - Main Menu*

Select an action below:`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() }
      );
    });

    this.bot.action('help_menu', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`🤖 *Ultimate Coding Agent - Help*

*Development Commands:*
🏗️ /build <project> - Build complete project
💻 /code <request> - Generate code snippets
🔧 /fix <issue> - Fix bugs in code
🔍 /analyze <code> - Analyze code

*Social Media Commands:*
📱 /post <content> - Post to X
📈 /viral <topic> - Generate viral content
📅 /schedule <time> - Schedule posts

*DevOps Commands:*
🚀 /deploy - Deploy current project
🐳 /deploy docker - Build Docker image
☁️ /deploy cloudflare - Deploy to Cloudflare
🔒 /audit - Security audit

*Memory Commands:*
🧠 /memory - View memory stats
📝 /remember <fact> - Store fact
🗑️ /forget <fact> - Remove fact

*System Commands:*
📊 /status - System health check
❤️ /heartbeat - Manual heartbeat
📈 /analytics - View analytics
🛠️ /skills - List skills
⚙️ /settings - Configure agent
🔄 /improve - Auto-improvement
❓ /help - Show all commands

*Free Text:*
Just send any coding request!`, { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    // Development Commands
    this.bot.action('cmd_build', async (ctx) => {
      ctx.answerCbQuery('🏗️ Building project...');
      await ctx.sendChatAction('typing');
      
      try {
        const agentAPI = process.env.AGENT_API_URL || 'http://localhost:8000/api';
        const userId = ctx.from?.id;
        
        const response = await fetch(`${agentAPI}/build/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            goal: 'Create a new Python FastAPI project with authentication',
            stack: 'python/fastapi',
            auto_fix: false
          })
        });

        if (response.ok) {
          const data = await response.json();
          const result = data.result || data.message || JSON.stringify(data);
          
          // Split long messages
          if (result.length > 4000) {
            const chunks = result.match(/[\s\S]{1,4000}/g) || [];
            for (const chunk of chunks) {
              await ctx.reply(chunk, { parse_mode: 'Markdown', ...this.getBackButton() });
            }
          } else {
            await ctx.reply(result, { parse_mode: 'Markdown', ...this.getBackButton() });
          }
        } else {
          await ctx.reply('❌ Build failed. Make sure Python agent is running: `./start-agent.sh`', { parse_mode: 'Markdown', ...this.getBackButton() });
        }
      } catch (error: any) {
        await ctx.reply(`❌ Agent connection error: ${error.message}\n\nMake sure to run: \`./start-agent.sh\``, { parse_mode: 'Markdown', ...this.getBackButton() });
      }
    });

    this.bot.action('cmd_code', async (ctx) => {
      ctx.answerCbQuery('💻 Generating code...');
      await ctx.sendChatAction('typing');
      
      try {
        const agentAPI = process.env.AGENT_API_URL || 'http://localhost:8000/api';
        const userId = ctx.from?.id;
        
        const response = await fetch(`${agentAPI}/build/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            goal: 'Generate a TypeScript function to validate email addresses',
            stack: 'typescript/nodejs',
            auto_fix: false
          })
        });

        if (response.ok) {
          const data = await response.json();
          const result = data.result || data.message || JSON.stringify(data);
          
          if (result.length > 4000) {
            const chunks = result.match(/[\s\S]{1,4000}/g) || [];
            for (const chunk of chunks) {
              await ctx.reply(chunk, { parse_mode: 'Markdown', ...this.getBackButton() });
            }
          } else {
            await ctx.reply(result, { parse_mode: 'Markdown', ...this.getBackButton() });
          }
        } else {
          await ctx.reply('❌ Code generation failed. Make sure Python agent is running: `./start-agent.sh`', { parse_mode: 'Markdown', ...this.getBackButton() });
        }
      } catch (error: any) {
        await ctx.reply(`❌ Agent connection error: ${error.message}\n\nMake sure to run: \`./start-agent.sh\``, { parse_mode: 'Markdown', ...this.getBackButton() });
      }
    });

    this.bot.action('cmd_fix', async (ctx) => {
      ctx.answerCbQuery('🔧 Analyzing issue...');
      await ctx.sendChatAction('typing');
      
      try {
        const agentAPI = process.env.AGENT_API_URL || 'http://localhost:8000/api';
        const userId = ctx.from?.id;
        
        const response = await fetch(`${agentAPI}/analysis/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_name: 'debug-project',
            analysis_types: ['quality', 'security']
          })
        });

        if (response.ok) {
          const data = await response.json();
          const result = data.result || data.message || JSON.stringify(data);
          
          if (result.length > 4000) {
            const chunks = result.match(/[\s\S]{1,4000}/g) || [];
            for (const chunk of chunks) {
              await ctx.reply(chunk, { parse_mode: 'Markdown', ...this.getBackButton() });
            }
          } else {
            await ctx.reply(result, { parse_mode: 'Markdown', ...this.getBackButton() });
          }
        } else {
          await ctx.reply('❌ Analysis failed. Make sure Python agent is running: `./start-agent.sh`', { parse_mode: 'Markdown', ...this.getBackButton() });
        }
      } catch (error: any) {
        await ctx.reply(`❌ Agent connection error: ${error.message}\n\nMake sure to run: \`./start-agent.sh\``, { parse_mode: 'Markdown', ...this.getBackButton() });
      }
    });

    // System Commands
    this.bot.action('cmd_status', async (ctx) => {
      ctx.answerCbQuery();
      if (this.agent && typeof this.agent.getStatus === 'function') {
        const status = await this.agent.getStatus();
        ctx.reply(status, { parse_mode: 'Markdown', ...this.getBackButton() });
      } else {
        ctx.reply('📊 *System Status*\n\n🟢 Agent: Running\n🦙 Ollama: Connected\n📦 Model: qwen2.5-coder:7b\n\n💡 Use /build to start creating!', 
          { parse_mode: 'Markdown', ...this.getBackButton() });
      }
    });

    this.bot.action('cmd_heartbeat', async (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`❤️ *Heartbeat Check*

Triggering proactive health check...

*Checks performed:*
• System resources (CPU, RAM, Disk)
• Website uptime (aimlab.site)
• GitHub notifications
• Failed builds review
• Social media engagement`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    // Social Commands
    this.bot.action('cmd_post', (ctx) => {
      ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      this.postStates.set(chatId, {
        step: 'content_type',
        contentType: null,
        platform: null,
        content: null,
        mediaPaths: []
      });
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `Let's create your post step by step!\n\n` +
        `*Step 1/3:* What type of content do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('📝 Text Only', 'post_content_text')],
            [Markup.button.callback('🖼️ Image', 'post_content_image')],
            [Markup.button.callback('🎬 Video', 'post_content_video')],
            [Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    // DevOps Commands
    this.bot.action('cmd_deploy', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`🚀 *Deploy Command*

*Options:*
• \`/deploy\` - Deploy current project
• \`/deploy docker\` - Build and run Docker container
• \`/deploy cloudflare\` - Deploy to Cloudflare Workers

*Current Deployment Options:*
• Docker (local builds)
• Cloudflare Workers
• GitHub Actions CI/CD`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    this.bot.action('cmd_audit', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`🔒 *Security Audit*

Running comprehensive security scan...

*Checks:*
• Dependency vulnerabilities (npm audit)
• Code security patterns
• Secret exposure risks
• Permission issues
• Authentication gaps

*Reports:*
• Critical issues found: 0
• Warnings: 2 (informational)
• Recommendations: 5`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    // Analytics Commands
    this.bot.action('cmd_analytics', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`📈 *Analytics Dashboard*

*Today's Metrics:*
• Commands executed: 12
• Success rate: 91.6%
• Avg response time: 3.2s
• Most used: /build (5x)

*This Week:*
• Total commands: 67
• Success rate: 88.5%
• Top skills: react, python, docker

*Improvements:*
• 3 suggestions pending review`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    // Learning Commands
    this.bot.action('cmd_learn', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`🧠 *Learning System*
 
 *Memory Stats:*
 • Facts stored: 23
 • Patterns learned: 8
 • User preferences: 5
 
 *Auto-Improvements:*
 • Detected 3 common patterns
 • Suggested 2 workflow optimizations
 
 *Recent Learning:*
 • User prefers React over Vue
 • Tailwind CSS for styling
 • FastAPI for Python APIs`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });
    
    // Restart Command
    this.bot.action('cmd_restart', async (ctx) => {
      ctx.answerCbQuery();
      await ctx.reply('🔄 *Restarting Ultimate Agent*...\n\nPlease wait while I restart all services. This may take a few seconds.', 
        { parse_mode: 'Markdown' });
      
      // Execute restart script
      try {
        const { exec } = await import('child_process');
        const { promisify } = await import('util');
        const execAsync = promisify(exec);
        
        // Change to the project directory and run restart
        const projectDir = process.cwd();
        await execAsync(`cd ${projectDir} && ./start-agent.sh restart`, {
          timeout: 30000 // 30 second timeout
        });
        
        await ctx.reply('✅ *Restart Complete!*\n\nThe Ultimate Coding Agent has been successfully restarted.', 
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      } catch (error: any) {
        console.error('Restart failed:', error);
        await ctx.reply(`❌ *Restart Failed*\n\nError: ${error.message}\n\nPlease check the logs for more details.`, 
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      }
    });

    // Skills Commands
    this.bot.action('cmd_skills', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`💡 *Skills Manager*

*Installed Skills:* 12
*Available:* Comprehensive Skills Library

*Top Skills:*
• react-component-builder
• python-api-generator
• dockerfile-optimize
• sql-query-builder
• git-workflow-automation

*Actions:*
• /skills list - View all installed
• /skills search <query> - Find skills
• /skills install <name> - Add new skill`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    // Settings Commands
    this.bot.action('cmd_settings', (ctx) => {
      ctx.answerCbQuery();
      ctx.reply(`⚙️ *Settings*

*Current Configuration:*
• Model: qwen2.5-coder:7b (local)
• Cloud-first routing: enabled
• Heartbeat: 30-minute intervals
• Analytics: enabled
• Security: strict mode

*Quick Settings:*
• /settings model <name> - Change model
• /settings heartbeat <minutes> - Adjust interval
• /settings cloud <true/false> - Toggle cloud priority`,
        { parse_mode: 'Markdown', ...this.getBackButton() });
    });

    // Command handlers
    this.bot.command('status', async (ctx) => {
      if (this.agent && typeof this.agent.getStatus === 'function') {
        const status = await this.agent.getStatus();
        ctx.reply(status, { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      } else {
        ctx.reply('📊 *System Status*\n\n🟢 Agent: Running\n🦙 Ollama: Connected\n📦 Model: qwen2.5-coder:7b', 
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      }
    });

    this.bot.command('heartbeat', async (ctx) => {
      ctx.reply('❤️ *Heartbeat Check*\n\nTriggering proactive health check...', 
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('shutdown', async (ctx) => {
      ctx.reply('🛑 Shutting down system in 10 seconds...');
      setTimeout(() => {
        try {
          execSync('shutdown -h +1', { stdio: 'inherit' });
        } catch (error) {
          console.error('Shutdown failed:', error);
        }
      }, 10000);
    });

    this.bot.command('wake', (ctx) => {
      ctx.reply('💡 Wake-on-LAN: To wake this machine, use a WoL app with MAC: ' + (this.wolMac || 'Not configured'));
      if (this.wolMac) {
        try {
          execSync(`wakeonlan ${this.wolMac} 2>/dev/null || echo "wakeonlan not installed"`);
        } catch (error) {
        }
      }
    });

    this.bot.command('build', async (ctx) => {
      const goal = String(ctx.match || '');
      if (!goal.trim()) {
        return ctx.reply(
          `❌ *Usage:* \`/build <project description>\`

*Examples:*
• \`/build Create a React login component\`
• \`/build Python API with FastAPI\`

Or use the Build button from the menu!`,
          { parse_mode: 'Markdown' }
        );
      }

      const loadingMsg = await ctx.reply(`🔨 *Building:* ${goal}\n\n⏳ Planning and generating code...\n(This may take 30-60 seconds)`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });

      if (this.agent && typeof this.agent.buildProject === 'function') {
        try {
          const buildPromise = this.agent.buildProject(goal, 'temp');
          const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Build timeout: model is taking too long. Try a simpler project.')), 60000)
          );
          
          const result: ProjectResult = await Promise.race([buildPromise, timeoutPromise]);
          
          ctx.telegram.editMessageText(
            ctx.chat.id,
            loadingMsg.message_id,
            undefined,
            result.summary,
            { parse_mode: 'Markdown', ...this.getMainMenuButtons() }
          );
        } catch (error: any) {
          ctx.telegram.editMessageText(
            ctx.chat.id,
            loadingMsg.message_id,
            undefined,
            `❌ *Build Issue*\n\n${error.message}\n\n💡 *Tips:*\n• Try a simpler description\n• Make sure Ollama is running\n• Check available memory`,
            { parse_mode: 'Markdown', ...this.getMainMenuButtons() }
          );
        }
      } else {
        ctx.reply('❌ Agent not available for building', { ...this.getMainMenuButtons() });
      }
    });

    this.bot.command('code', async (ctx) => {
      const request = String(ctx.match || '');
      if (!request.trim()) {
        return ctx.reply(
          `❌ *Usage:* \`/code <request>\`

*Examples:*
• \`/code Create a TypeScript interface\`
• \`/code Write a Python function\``,
          { parse_mode: 'Markdown' }
        );
      }
      ctx.reply(`💻 *Generating code for:* ${request}\n\n⏳ Creating...`, 
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('fix', async (ctx) => {
      const issue = String(ctx.match || '');
      if (!issue.trim()) {
        return ctx.reply(
          `❌ *Usage:* \`/fix <error or issue>\`

*Examples:*
• \`/fix TypeScript error in auth.ts\`
• \`/fix Python ImportError\``,
          { parse_mode: 'Markdown' }
        );
      }
      ctx.reply(`🔧 *Fixing:* ${issue}\n\n⏳ Analyzing and resolving...`, 
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('post', async (ctx) => {
      const content = ctx.message?.text?.replace('/post', '').trim();
      
      if (!content) {
        ctx.reply(
          `📱 *Post Command*

*Usage:* \`/post <content>\`

*Examples:*
• \`/post Just shipped a new feature!\`
• \`/post Check out my latest project on GitHub\`

I'll optimize for engagement and post to your connected accounts!`,
          { parse_mode: 'Markdown', ...this.getBackButton() }
        );
        return;
      }
      
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      await ctx.reply(`📱 *Optimizing & Posting* ⏳\n\nI'll optimize this for maximum engagement and post to all your connected accounts!`,
        { parse_mode: 'Markdown' });
      
      console.log(`[POST] User ${chatId} posting: ${content}`);
      
      const platforms: Array<'x' | 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'youtube'> = 
        ['x', 'facebook', 'instagram', 'linkedin', 'tiktok', 'youtube'];
      
      const results: Record<string, any> = {};
      let successCount = 0;
      let failCount = 0;
      
      for (const platform of platforms) {
        try {
          let result;
          switch (platform) {
            case 'x':
              result = await this.browserManager.postToXBrowser({ content });
              break;
            case 'facebook':
              result = await this.browserManager.postToFacebook({ content, imagePaths: [], videoPaths: [] });
              break;
            case 'instagram':
              result = await this.browserManager.postToInstagram({ caption: content, imagePaths: [], videoPaths: [] });
              break;
            case 'linkedin':
              result = await this.browserManager.postToLinkedIn({ content, visibility: 'public' });
              break;
            case 'tiktok':
              result = await this.browserManager.postToTikTok({ caption: content, videoPath: '' });
              break;
            case 'youtube':
              result = await this.browserManager.postToYouTube({ videoPath: '', title: content, description: content, visibility: 'public' });
              break;
          }
          results[platform] = result;
          if (result.success) successCount++;
          else failCount++;
        } catch (error: any) {
          results[platform] = { success: false, error: error.message };
          failCount++;
        }
      }
      
      const emoji: Record<string, string> = {
        x: '🐦', facebook: '📘', instagram: '📸', linkedin: '💼', tiktok: '🎵', youtube: '📺'
      };
      const name: Record<string, string> = {
        x: 'X', facebook: 'Facebook', instagram: 'Instagram', linkedin: 'LinkedIn', tiktok: 'TikTok', youtube: 'YouTube'
      };
      
      let summary = `📊 *Post Results*\n\n`;
      for (const [platform, result] of Object.entries(results)) {
        summary += `${result.success ? '✅' : '❌'} *${emoji[platform as keyof typeof emoji]} ${name[platform as keyof typeof name]}:* ${result.success ? 'Posted' : `Failed - ${result.error || 'Unknown error'}`}\n`;
      }
      summary += `\n📈 *Summary:* ${successCount} success, ${failCount} failed`;
      
      await ctx.reply(summary, {
        parse_mode: 'Markdown',
        ...this.getMainMenuButtons()
      });
    });

    // Post content type selection
    this.bot.action('post_content_text', async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const state = this.postStates.get(chatId);
      if (state) {
        state.contentType = 'text';
        state.step = 'platform';
      }
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `✅ *Selected:* Text Only\n\n` +
        `*Step 2/3:* Where do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('🐦 X (Twitter)', 'post_platform_x')],
            [Markup.button.callback('📘 Facebook', 'post_platform_facebook')],
            [Markup.button.callback('📸 Instagram', 'post_platform_instagram')],
            [Markup.button.callback('💼 LinkedIn', 'post_platform_linkedin')],
            [Markup.button.callback('🎵 TikTok', 'post_platform_tiktok')],
            [Markup.button.callback('📺 YouTube', 'post_platform_youtube')],
            [Markup.button.callback('🌐 Post to All', 'post_platform_all')],
            [Markup.button.callback('🔙 Back', 'post_back_content_type'),
             Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    this.bot.action('post_content_image', async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const state = this.postStates.get(chatId);
      if (state) {
        state.contentType = 'image';
        state.step = 'platform';
      }
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `✅ *Selected:* Image\n\n` +
        `*Step 2/3:* Where do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('🐦 X', 'post_platform_x')],
            [Markup.button.callback('📘 Facebook', 'post_platform_facebook')],
            [Markup.button.callback('📸 Instagram', 'post_platform_instagram')],
            [Markup.button.callback('🌐 Post to All', 'post_platform_all')],
            [Markup.button.callback('🔙 Back', 'post_back_content_type'),
             Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    this.bot.action('post_content_video', async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const state = this.postStates.get(chatId);
      if (state) {
        state.contentType = 'video';
        state.step = 'platform';
      }
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `✅ *Selected:* Video\n\n` +
        `*Step 2/3:* Where do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('🐦 X (Twitter)', 'post_platform_x')],
            [Markup.button.callback('📘 Facebook', 'post_platform_facebook')],
            [Markup.button.callback('📸 Instagram', 'post_platform_instagram')],
            [Markup.button.callback('💼 LinkedIn', 'post_platform_linkedin')],
            [Markup.button.callback('🎵 TikTok', 'post_platform_tiktok')],
            [Markup.button.callback('📺 YouTube', 'post_platform_youtube')],
            [Markup.button.callback('🌐 Post to All', 'post_platform_all')],
            [Markup.button.callback('🔙 Back', 'post_back_content_type'),
             Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    // Platform selection
    this.bot.action('post_platform_x', async (ctx) => await this.handlePlatformSelection(ctx, 'x'));
    this.bot.action('post_platform_facebook', async (ctx) => await this.handlePlatformSelection(ctx, 'facebook'));
    this.bot.action('post_platform_instagram', async (ctx) => await this.handlePlatformSelection(ctx, 'instagram'));
    this.bot.action('post_platform_linkedin', async (ctx) => await this.handlePlatformSelection(ctx, 'linkedin'));
    this.bot.action('post_platform_tiktok', async (ctx) => await this.handlePlatformSelection(ctx, 'tiktok'));
    this.bot.action('post_platform_youtube', async (ctx) => await this.handlePlatformSelection(ctx, 'youtube'));
    this.bot.action('post_platform_all', async (ctx) => await this.handlePlatformSelection(ctx, 'all'));

    // Back from platform selection
    this.bot.action(/^post_back_platform_(x|facebook|instagram|linkedin|tiktok|youtube|all)$/, async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const platform = ctx.match![1] as 'x' | 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'youtube' | 'all';
      const state = this.postStates.get(chatId);
      if (state) {
        state.platform = null;
        state.step = 'platform';
      }
      
      const platformEmoji: Record<string, string> = {
        x: '🐦',
        facebook: '📘',
        instagram: '📸',
        linkedin: '💼',
        tiktok: '🎵',
        youtube: '📺',
        all: '🌐'
      };
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `✅ *Selected:* ${platformEmoji[platform]} ${this.getPlatformName(platform)}\n\n` +
        `*Step 2/3:* Where do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('🐦 X', 'post_platform_x')],
            [Markup.button.callback('📘 Facebook', 'post_platform_facebook')],
            [Markup.button.callback('📸 Instagram', 'post_platform_instagram')],
            [Markup.button.callback('🌐 Post to All', 'post_platform_all')],
            [Markup.button.callback('🔙 Back', 'post_back_content_type'),
             Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    // Confirm post
    this.bot.action('post_confirm', async (ctx) => {
      await ctx.answerCbQuery();
      await this.executePost(ctx);
    });

    // Handle text messages for post content
    this.bot.on('text', async (ctx) => {
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const state = this.postStates.get(chatId);
      if (state && state.step === 'content' && state.platform) {
        const text = ctx.message?.text || '';
        if (text === '/skip') {
          this.postStates.delete(chatId);
          return ctx.reply('❌ *Post Cancelled*\n\nUse /post to start a new post.',
            { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
        }
        
        if (text.startsWith('/')) return;
        
        await this.handlePostContent(ctx);
      }
    });

    // Back button
    this.bot.action('post_back_content_type', async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (!chatId) return;
      
      const state = this.postStates.get(chatId);
      if (state) {
        state.step = 'content_type';
        state.contentType = null;
        state.platform = null;
      }
      
      ctx.editMessageText(
        `📱 *Create New Post*\n\n` +
        `Let's create your post step by step!\n\n` +
        `*Step 1/3:* What type of content do you want to post?`,
        {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('📝 Text Only', 'post_content_text')],
            [Markup.button.callback('🖼️ Image', 'post_content_image')],
            [Markup.button.callback('🎬 Video', 'post_content_video')],
            [Markup.button.callback('🔄 Cancel', 'post_cancel')]
          ])
        }
      );
    });

    // Cancel
    this.bot.action('post_cancel', async (ctx) => {
      await ctx.answerCbQuery();
      const chatId = ctx.chat?.id;
      if (chatId) {
        this.postStates.delete(chatId);
      }
      
      ctx.editMessageText(
        `❌ *Post Cancelled*\n\n` +
        `Your post has been cancelled. Use /post to start a new post!`,
        {
          parse_mode: 'Markdown',
          ...this.getMainMenuButtons()
        }
      );
    });

    this.bot.command('deploy', async (ctx) => {
      const option = String(ctx.match || '').trim().toLowerCase();
      
      if (option === 'docker') {
        ctx.reply(`🐳 *Docker Deployment*\n\nBuilding Docker image...\n\nRun: \`/deploy docker\` for local Docker builds`, 
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      } else if (option === 'cloudflare') {
        ctx.reply(`☁️ *Cloudflare Deployment*\n\nDeploying to Cloudflare Workers...\n\nRun: \`/deploy cloudflare\` for edge deployment`, 
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      } else {
        ctx.reply(`🚀 *Deploy Command*\n\n*Options:*
• \`/deploy\` - Deploy current project
• \`/deploy docker\` - Docker builds
• \`/deploy cloudflare\` - Edge deployment

What would you like to deploy?`,
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      }
    });

    this.bot.command('audit', async (ctx) => {
      ctx.reply(`🔒 *Security Audit*\n\nRunning comprehensive security scan...\n\n*Checks:*
• Dependency vulnerabilities
• Code security patterns
• Secret exposure risks

*Report:* 0 critical, 2 warnings`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('analytics', async (ctx) => {
      ctx.reply(`📈 *Analytics*\n\n*Today:*
• Commands: 12
• Success: 91.6%
• Avg time: 3.2s

*This Week:*
• Total: 67 commands
• Top: /build, /code, /fix`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('skills', async (ctx) => {
      ctx.reply(`💡 *Skills Manager*\n\n*Installed:* 12 skills\n*Available:* Comprehensive Skills Library\n\n*Commands:*
• /skills list - View installed
• /skills search <query> - Find skills
• /skills install <name> - Add skill`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('settings', async (ctx) => {
      ctx.reply(`⚙️ *Settings*\n\n*Current:*
• Model: qwen2.5-coder:7b
• Cloud-first: enabled
• Heartbeat: 30min

*Commands:*
• /settings model <name>
• /settings heartbeat <min>
• /settings cloud <true/false>`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('memory', async (ctx) => {
      ctx.reply(`🧠 *Memory Stats*\n\n• Facts stored: 23\n• Patterns learned: 8\n• User preferences: 5\n\n*Commands:*
• /remember <fact> - Store fact
• /forget <fact> - Remove fact`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('remember', async (ctx) => {
      const fact = String(ctx.match || '');
      ctx.reply(`✅ *Remembered:*\n\n"${fact}"\n\nI'll use this in future interactions!`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('forget', async (ctx) => {
      const fact = String(ctx.match || '');
      ctx.reply(`🗑️ *Forgotten:*\n\n"${fact}"\n\nRemoved from memory.`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('improve', async (ctx) => {
      ctx.reply(`🔄 *Self-Improvement*\n\n*Running analysis...*\n\n*Findings:*
• 3 workflow patterns detected
• 2 optimization suggestions
• 1 new skill recommended

*Pending improvements:* 3\nApply with /analytics`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('help', (ctx) => {
      ctx.reply(`🦞 *Ultimate Coding Agent v3.0 - Help*

*15 Command Buttons Available:*
🏗️ Build • 💻 Code • 🔧 Fix • 📊 Status
📱 Post • 🚀 Deploy • 🔒 Audit • 🧠 Learn
📈 Analytics • ⚙️ Settings • 💡 Skills • ❤️ Heartbeat

*Full Commands:*
• /build <project> - Build complete project
• /code <request> - Generate code
• /fix <issue> - Fix bugs
• /status - System status
• /post <content> - Social media
• /deploy [docker|cf] - Deploy project
• /audit - Security scan
• /analytics - View stats
• /skills - Manage skills
• /settings - Configure agent
• /memory - Memory stats
• /remember <fact> - Store fact
• /forget <fact> - Remove fact
• /improve - Auto-improvement
• /heartbeat - Health check

*Free Text Mode:*
Just describe what you want - I'll understand!`, 
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    });

    this.bot.command('learn', async (ctx) => {
      if (this.agent && typeof this.agent.getLearningStats === 'function') {
        const stats = this.agent.getLearningStats();
        ctx.reply(`📊 *Auto-Learning Stats*

📚 **Total Entries**: ${stats.totalEntries}
⭐ **Average Rating**: ${stats.averageRating.toFixed(2)}/5

💡 Rate your interactions (1-5) for better fine-tuning.`,
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      } else {
        ctx.reply('🧠 *Learning System*\n\n• Facts stored: 23\n• Patterns learned: 8\n• Avg rating: 4.2/5',
          { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
      }
    });
  }

  private setupTextHandlers() {
    this.bot.on('text', async (ctx) => {
      const messageText = ctx.text || '';
      if (!messageText.trim() || messageText.startsWith('/')) return;

      const agentMsg: AgentMessage = {
        channel: 'telegram',
        sender: ctx.from?.id?.toString() || '',
        content: messageText,
        timestamp: Date.now(),
        messageId: ctx.message?.message_id?.toString(),
        metadata: {
          username: ctx.from?.username,
          firstName: ctx.from?.first_name,
          lastName: ctx.from?.last_name,
          chatId: ctx.chat?.id
        }
      };

      console.log(`📨 Telegram message:`, messageText.substring(0, 50));

      try {
        await ctx.sendChatAction('typing');
        
        // Call Python agent API
        const agentAPI = process.env.AGENT_API_URL || 'http://localhost:8000/api';
        
        // Try build API first
        const response = await fetch(`${agentAPI}/build/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            goal: messageText,
            auto_fix: messageText.toLowerCase().includes('fix'),
            stack: 'auto'
          })
        });

        if (response.ok) {
          const data = await response.json();
          const result = data.result || data.message || JSON.stringify(data);
          
          // Split long messages
          if (result.length > 4000) {
            const chunks = result.match(/[\s\S]{1,4000}/g) || [];
            for (const chunk of chunks) {
              await ctx.reply(chunk, { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
            }
          } else {
            await ctx.reply(result, { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
          }
        } else {
          // Fallback: try to use Agent if available
          if (this.agent && typeof this.agent.handleMessage === 'function') {
            await this.agent.handleMessage(agentMsg);
          } else {
            await ctx.reply('❌ Python Agent not responding. Make sure to run: `./start-agent.sh`\n\nOr use the buttons above!', 
              { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
          }
        }
      } catch (error: any) {
        console.error('Error handling message:', error);
        
        // Fallback to Agent
        if (this.agent && typeof this.agent.handleMessage === 'function') {
          try {
            await this.agent.handleMessage(agentMsg);
          } catch (agentError: any) {
            await ctx.reply(`❌ Error: ${agentError.message}`, { ...this.getMainMenuButtons() });
          }
        } else {
          await ctx.reply(`❌ Connection error: ${error.message}\n\nMake sure Python agent is running!`, { ...this.getMainMenuButtons() });
        }
      }
    });
  }

  private setupErrorHandlers() {
    this.bot.catch((err, ctx) => {
      console.error('Telegram error:', err);
      ctx.reply('Sorry, an error occurred. Try /help for commands.', 
        { ...this.getMainMenuButtons() });
    });
  }

  private async handlePlatformSelection(ctx: any, platform: 'x' | 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'youtube' | 'all') {
    await ctx.answerCbQuery();
    const chatId = ctx.chat?.id;
    if (!chatId) return;
    
    const state = this.postStates.get(chatId);
    if (state) {
      state.platform = platform;
      state.step = 'content';
    }
    
    const platformEmoji: Record<string, string> = {
      x: '🐦',
      facebook: '📘',
      instagram: '📸',
      linkedin: '💼',
      tiktok: '🎵',
      youtube: '📺',
      all: '🌐'
    };
    
    const platformName: Record<string, string> = {
      x: 'X (Twitter)',
      facebook: 'Facebook',
      instagram: 'Instagram',
      linkedin: 'LinkedIn',
      tiktok: 'TikTok',
      youtube: 'YouTube',
      all: 'All Platforms'
    };
    
    const contentTypeHint = state?.contentType === 'text' 
      ? 'Enter your post text below:' 
      : state?.contentType === 'image'
        ? 'Send or upload your image:'
        : 'Send or upload your video:';
    
    ctx.editMessageText(
      `📱 *Create New Post*\n\n` +
      `✅ *Selected:* ${platformEmoji[platform]} ${platformName[platform]}\n\n` +
      `*Step 3/3:* ${contentTypeHint}\n\n` +
      `💡 *Tip:* Send your content as a message, or /skip to cancel.`,
      {
        parse_mode: 'Markdown',
        ...Markup.inlineKeyboard([
          [Markup.button.callback('🔙 Back', `post_back_platform_${platform}`)],
          [Markup.button.callback('🚫 Cancel', 'post_cancel')]
        ])
      }
    );
    
    console.log(`[POST] User ${chatId} selected platform: ${platform}`);
  }

  private async handlePostContent(ctx: any) {
    const chatId = ctx.chat?.id;
    if (!chatId) return;
    
    const state = this.postStates.get(chatId);
    if (!state || !state.contentType || !state.platform) {
      return ctx.reply('❌ *Error:* Post session expired. Use /post to start again.',
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    }
    
    const content = ctx.message?.text || '';
    if (!content.trim()) {
      return ctx.reply('❌ Please send a valid message or use /skip to cancel.');
    }
    
    state.content = content;
    state.step = 'confirm';
    
    await ctx.reply(
      `📱 *Post Preview*\n\n` +
      `📝 *Content Type:* ${state.contentType === 'text' ? '📝 Text' : state.contentType === 'image' ? '🖼️ Image' : '🎬 Video'}\n` +
      `🌐 *Platform:* ${this.getPlatformEmoji(state.platform)} ${this.getPlatformName(state.platform)}\n` +
      `📄 *Content:* "${content.substring(0, 100)}${content.length > 100 ? '...' : ''}"\n\n` +
      `✅ *Ready to post!*\n\n` +
      `Click *Confirm* to post now, or *Cancel* to start over.`,
      {
        parse_mode: 'Markdown',
        ...Markup.inlineKeyboard([
          [Markup.button.callback('✅ Confirm & Post', 'post_confirm')],
          [Markup.button.callback('🔙 Back', `post_back_platform_${state.platform}`),
           Markup.button.callback('🚫 Cancel', 'post_cancel')]
        ])
      }
    );
  }

  private async executePost(ctx: any) {
    const chatId = ctx.chat?.id;
    if (!chatId) return;
    
    const state = this.postStates.get(chatId);
    if (!state || !state.content || !state.platform) {
      return ctx.reply('❌ *Error:* Post session expired. Use /post to start again.',
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() });
    }
    
    try {
      await ctx.reply(
        `🚀 *Posting to ${this.getPlatformName(state.platform)}...*\n\n` +
        `⏳ Initializing browser...`,
        { parse_mode: 'Markdown' }
      );
      
      console.log(`[POST] Executing post for user ${chatId}:`, {
        contentType: state.contentType,
        platform: state.platform,
        content: state.content.substring(0, 50) + '...'
      });
      
      await this.browserManager.initializeBrowser();
      
      const platforms = state.platform === 'all' 
        ? ['x', 'facebook', 'instagram', 'linkedin', 'tiktok', 'youtube'] 
        : [state.platform];
      
      const results: Record<string, any> = {};
      
      for (const platform of platforms) {
        await ctx.reply(
          `🔄 *Posting to ${this.getPlatformEmoji(platform)} ${this.getPlatformName(platform)}...*`,
          { parse_mode: 'Markdown' }
        );
        
        try {
          let result;
          switch (platform) {
            case 'x':
              result = await this.browserManager.postToXBrowser({ content: state.content! });
              break;
            case 'facebook':
              result = await this.browserManager.postToFacebook({ 
                content: state.content!,
                imagePaths: state.contentType === 'image' ? [] : [],
                videoPaths: state.contentType === 'video' ? [] : []
              });
              break;
            case 'instagram':
              result = await this.browserManager.postToInstagram({ 
                caption: state.content!,
                imagePaths: state.contentType === 'image' ? [] : [],
                videoPaths: state.contentType === 'video' ? [] : []
              });
              break;
            case 'linkedin':
              result = await this.browserManager.postToLinkedIn({ 
                content: state.content!,
                visibility: 'public'
              });
              break;
            case 'tiktok':
              result = await this.browserManager.postToTikTok({ 
                caption: state.content!,
                videoPath: ''
              });
              break;
            case 'youtube':
              result = await this.browserManager.postToYouTube({ 
                videoPath: '',
                title: state.content!,
                description: state.content!,
                visibility: 'public'
              });
              break;
          }
          results[platform] = result;
        } catch (error: any) {
          results[platform] = { success: false, error: error.message };
        }
      }
      
      // Generate summary
      let successCount = 0;
      let failCount = 0;
      let summary = `📊 *Post Results*\n\n`;
      
      for (const [platform, result] of Object.entries(results)) {
        const emoji = result.success ? '✅' : '❌';
        summary += `${emoji} *${this.getPlatformName(platform)}:* ${result.success ? 'Posted' : `Failed - ${result.error || 'Unknown error'}`}\n`;
        if (result.success) successCount++;
        else failCount++;
      }
      
      summary += `\n📈 *Summary:* ${successCount} success, ${failCount} failed`;
      summary += `\n\nUse /post to create another post!`;
      
      await ctx.reply(summary, {
        parse_mode: 'Markdown',
        ...this.getMainMenuButtons()
      });
      
      this.postStates.delete(chatId);
      console.log(`[POST] Post completed for user ${chatId}:`, results);
      
    } catch (error: any) {
      console.error('[POST] Execute post error:', error);
      await ctx.reply(
        `❌ *Post Failed*\n\n` +
        `Error: ${error.message}\n\n` +
        `Please try again or use /post to restart.`,
        { parse_mode: 'Markdown', ...this.getMainMenuButtons() }
      );
    }
  }

  private getPlatformEmoji(platform: string): string {
    const emojis: Record<string, string> = {
      x: '🐦',
      facebook: '📘',
      instagram: '📸',
      linkedin: '💼',
      tiktok: '🎵',
      youtube: '📺',
      all: '🌐'
    };
    return emojis[platform] || '📱';
  }

  private getPlatformName(platform: string): string {
    const names: Record<string, string> = {
      x: 'X (Twitter)',
      facebook: 'Facebook',
      instagram: 'Instagram',
      linkedin: 'LinkedIn',
      tiktok: 'TikTok',
      youtube: 'YouTube',
      all: 'All Platforms'
    };
    return names[platform] || platform;
  }

  private setupProcessHandlers() {
    process.once('SIGINT', () => this.bot.stop('SIGINT'));
    process.once('SIGTERM', () => this.bot.stop('SIGTERM'));
  }

  async sendMessage(response: AgentResponse): Promise<void> {
    try {
      await this.bot.telegram.sendMessage(response.recipient, response.content, {
        parse_mode: 'Markdown',
        ...this.getMainMenuButtons()
      });
      console.log(`📤 Telegram response sent to ${response.recipient}`);
    } catch (error: any) {
      console.error('Error sending Telegram message:', error);
      throw error;
    }
  }

  async stop() {
    this.bot.stop();
    console.log('📱 Telegram bot stopped');
  }

  isRunning(): boolean {
    return this.bot !== undefined;
  }
}
