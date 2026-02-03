/*
  Chatty Agent Module for Telegram Bot
  Enables proactive, conversational interactions with users
*/

import { Telegraf, Context, Markup } from 'telegraf';

interface ChattyContext {
  userId: number;
  firstName: string;
  lastInteraction: Date;
  conversationCount: number;
  preferences: Map<string, string>;
}

interface ProactiveMessage {
  content: string;
  buttons?: Array<{
    emoji: string;
    label: string;
    callback_data: string;
  }>;
  delay?: number; // Delay in milliseconds before sending
}

export class ChattyAgent {
  private bot: Telegraf;
  private userContexts: Map<number, ChattyContext> = new Map();
  private adminId: string;
  private conversationStarters: ProactiveMessage[] = [
    {
      content: "💡 *Quick Idea:* Have you tried building something new today? I'm here to help with any coding project!",
      buttons: [
        { emoji: '🏗️', label: 'Build', callback_data: 'cmd_build' },
        { emoji: '💻', label: 'Code', callback_data: 'cmd_code' }
      ]
    },
    {
      content: "🚀 *Ready to Ship!* Need help deploying your latest project? I can help with Docker, Cloudflare, or traditional hosting!",
      buttons: [
        { emoji: '🚀', label: 'Deploy', callback_data: 'cmd_deploy' },
        { emoji: '🔧', label: 'Fix', callback_data: 'cmd_fix' }
      ]
    },
    {
      content: "📱 *Social Media Time!* Want to schedule or post updates across all your platforms? Just ask!",
      buttons: [
        { emoji: '📱', label: 'Post', callback_data: 'cmd_post' },
        { emoji: '📈', label: 'Analytics', callback_data: 'cmd_analytics' }
      ]
    },
    {
      content: "🧠 *Learning Mode:* I've picked up some new skills lately. Want to see what I can do?",
      buttons: [
        { emoji: '💡', label: 'Skills', callback_data: 'cmd_skills' },
        { emoji: '🧠', label: 'Learn', callback_data: 'cmd_learn' }
      ]
    }
  ];
  
  private welcomeMessages: ProactiveMessage[] = [
    {
      content: "👋 *Welcome back!* I'm excited to help you build something amazing today. What shall we work on?",
      delay: 1500
    },
    {
      content: "✨ *Ready for Action!* Just tell me what you need - whether it's coding, deploying, or fixing issues.",
      delay: 3000
    }
  ];

  constructor(bot: Telegraf, adminId: string) {
    this.bot = bot;
    this.adminId = adminId;
    this.setupChattyHandlers();
  }

  private setupChattyHandlers(): void {
    // Handle user start/interaction
    this.bot.on('message', async (ctx) => {
      const userId = ctx.from?.id;
      if (!userId || userId.toString() !== this.adminId) return;

      // Update user context
      this.updateUserContext(userId, ctx);

      // Send welcome message if new or after restart
      if (!this.userContexts.has(userId)) {
        await this.sendWelcomeSequence(ctx);
      }
    });

    // Handle callback queries to update conversation
    this.bot.on('callback_query', async (ctx) => {
      const userId = ctx.from?.id;
      if (!userId) return;

      const context = this.userContexts.get(userId);
      if (context) {
        context.conversationCount++;
        context.lastInteraction = new Date();
      }
    });
  }

  private async updateUserContext(ctx: Context, userId: number): Promise<void> {
    if (!ctx.from) return;

    let context = this.userContexts.get(userId);
    if (!context) {
      context = {
        userId,
        firstName: ctx.from.first_name || 'User',
        lastInteraction: new Date(),
        conversationCount: 0,
        preferences: new Map()
      };
      this.userContexts.set(userId, context);
    } else {
      context.lastInteraction = new Date();
    }
  }

  async sendWelcomeSequence(ctx: Context): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    // Send main welcome immediately
    await ctx.reply(
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

    // Send additional chatty messages with delay
    for (const msg of this.welcomeMessages) {
      if (msg.delay) {
        await new Promise(resolve => setTimeout(resolve, msg.delay));
      }
      
      await ctx.reply(msg.content, {
        parse_mode: 'Markdown',
        ...this.getMainMenuButtons()
      });
    }
  }

  async sendProactiveMessage(ctx: Context): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    // Select random conversation starter
    const randomIndex = Math.floor(Math.random() * this.conversationStarters.length);
    const message = this.conversationStarters[randomIndex];

    // Build keyboard from buttons
    const keyboard = message.buttons?.map(btn => 
      Markup.button.callback(`${btn.emoji} ${btn.label}`, btn.callback_data)
    );

    await ctx.reply(message.content, {
      parse_mode: 'Markdown',
      ...Markup.inlineKeyboard(keyboard || [])
    });
  }

  async handleChattyInteraction(ctx: Context, userMessage: string): Promise<string> {
    const userId = ctx.from?.id;
    if (!userId) return "I'm not sure who I'm talking to!";

    // Update context
    this.updateUserContext(ctx, userId);
    const context = this.userContexts.get(userId);
    
    if (context) {
      context.conversationCount++;
    }

    // Generate contextual response
    const response = this.generateContextualResponse(userMessage, context);
    
    return response;
  }

  private generateContextualResponse(message: string, context?: ChattyContext): string {
    const lowerMessage = message.toLowerCase();

    // Greetings
    if (['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'].some(g => lowerMessage.includes(g))) {
      const greetings = [
        `Hey there! 👋 How can I help you today?`,
        `Hi! 😊 Ready to build something amazing?`,
        `Hello! 🚀 What shall we work on?`,
        `Hey! ✨ I'm here to help with any coding tasks.`
      ];
      return greetings[Math.floor(Math.random() * greetings.length)];
    }

    // Help requests
    if (lowerMessage.includes('help') || lowerMessage.includes('what can you do')) {
      return `🤖 *I can help you with:*

• 🏗️ **Building** - Create complete projects from scratch
• 💻 **Coding** - Generate code snippets and solutions
• 🔧 **Fixing** - Debug and resolve issues in your code
• 🚀 **Deploying** - Ship projects to production
• 📱 **Social Media** - Post and schedule content
• 🔒 **Security** - Audit and secure your applications
• 🧠 **Learning** - Remember preferences and improve

Just tell me what you need!`;
    }

    // Status checks
    if (lowerMessage.includes('status') || lowerMessage.includes('how are you')) {
      return `📊 *System Status:*

🟢 Agent: Running smoothly
🧠 Model: Qwen3-Coder-Plus
💾 Memory: Active
📱 Telegram: Connected

What would you like to work on?`;
    }

    // Default response
    return `💬 *I understand you said:* "${message}"

I'm here to help with coding, building, deploying, and more! 

Try asking me to:
• Build a project
• Fix a bug
• Generate some code
• Deploy an application
• Post to social media

Or just tap one of the buttons below! 🤖`;
  }

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

  getUserStats(userId: number): { conversationCount: number; lastInteraction: Date } | null {
    const context = this.userContexts.get(userId);
    if (!context) return null;

    return {
      conversationCount: context.conversationCount,
      lastInteraction: context.lastInteraction
    };
  }

  clearUserContext(userId: number): void {
    this.userContexts.delete(userId);
  }
}

export default ChattyAgent;
