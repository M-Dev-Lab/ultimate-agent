/**
 * Telegram Agent Bridge
 * 
 * Connects core systems (OllamaClient, SkillSystem, MemoryManager, ErrorHandler, UnifiedAgent)
 * to the Telegram bot for seamless integration.
 * 
 * Handles:
 * - Message queuing and sequential processing
 * - Context extraction from Telegram messages
 * - Response formatting for Telegram
 * - Streaming response handling
 * - User session management
 */

import { Context } from 'telegraf';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs/promises';
import {
  initializeAgent,
  getAgent,
  shutdownAgent,
} from '../core/index.js';

interface TelegramUserSession {
  userId: number;
  username?: string;
  firstName?: string;
  lastName?: string;
  createdAt: number;
  lastMessageAt: number;
  messageCount: number;
}

interface BridgeConfig {
  dataDir: string;
  maxQueueSize: number;
  sessionTimeout: number; // milliseconds
  debugMode: boolean;
}

export class TelegramAgentBridge extends EventEmitter {
  private userSessions: Map<number, TelegramUserSession> = new Map();
  private messageQueue: Map<number, Array<{ ctx: Context; content: string; timestamp: number }>> = new Map();
  private processing: Map<number, boolean> = new Map();
  private config: BridgeConfig;
  private agentReady: boolean = false;

  constructor(config: Partial<BridgeConfig> = {}) {
    super();
    this.config = {
      dataDir: config.dataDir || path.join(process.cwd(), 'data', 'telegram-sessions'),
      maxQueueSize: config.maxQueueSize || 50,
      sessionTimeout: config.sessionTimeout || 3600000, // 1 hour
      debugMode: config.debugMode || false,
    };
  }

  /**
   * Initialize the bridge and core agent
   */
  async initialize(): Promise<void> {
    try {
      console.log('[Bridge] Initializing TelegramAgentBridge...');

      // Ensure data directory exists
      await fs.mkdir(this.config.dataDir, { recursive: true });

      // Initialize the unified agent
      const agent = await initializeAgent({
        userId: 'telegram-bot',
        model: process.env.OLLAMA_MODEL || 'qwen2.5-coder:7b',
        enableMemory: true,
        enableSkills: true,
        enableErrorHandling: true,
      });

      this.agentReady = true;
      console.log('[Bridge] ✅ TelegramAgentBridge initialized successfully');

      this.emit('ready');
    } catch (error) {
      console.error('[Bridge] ❌ Initialization failed:', error);
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Handle incoming Telegram message
   */
  async handleMessage(ctx: Context, userMessage: string): Promise<void> {
    try {
      if (!this.agentReady) {
        await ctx.reply('⏳ Agent is initializing... Please try again in a moment.');
        return;
      }

      const userId = ctx.from?.id;
      if (!userId) {
        console.error('[Bridge] No user ID in context');
        return;
      }

      // Get or create user session
      this.getOrCreateSession(userId, ctx.from);

      // Add to message queue
      this.queueMessage(userId, ctx, userMessage);

      // Process queue
      await this.processQueue(userId, ctx);
    } catch (error) {
      console.error('[Bridge] Error handling message:', error);
      await ctx.reply('❌ Error processing your message. Please try again.');
      this.emit('error', error);
    }
  }

  /**
   * Queue message for processing
   */
  private queueMessage(
    userId: number,
    ctx: Context,
    content: string
  ): void {
    if (!this.messageQueue.has(userId)) {
      this.messageQueue.set(userId, []);
    }

    const queue = this.messageQueue.get(userId)!;

    // Enforce max queue size
    if (queue.length >= this.config.maxQueueSize) {
      console.warn(`[Bridge] Queue full for user ${userId}, dropping oldest message`);
      queue.shift();
    }

    queue.push({
      ctx,
      content,
      timestamp: Date.now(),
    });
  }

  /**
   * Process message queue sequentially
   */
  private async processQueue(userId: number, ctx: Context): Promise<void> {
    // Prevent concurrent processing
    if (this.processing.get(userId)) {
      ctx.reply('⏳ Processing your previous message... Please wait.').catch(console.error);
      return;
    }

    this.processing.set(userId, true);

    try {
      while (true) {
        const queue = this.messageQueue.get(userId);
        if (!queue || queue.length === 0) {
          break;
        }

        const { ctx: msgCtx, content } = queue.shift()!;
        await this.processMessage(userId, msgCtx, content);
      }
    } finally {
      this.processing.set(userId, false);
    }
  }

  /**
   * Process single message through agent
   */
  private async processMessage(
    userId: number,
    ctx: Context,
    userMessage: string
  ): Promise<void> {
    const startTime = Date.now();

    try {
      console.log(`[Bridge] Processing message from user ${userId}: "${userMessage.substring(0, 50)}..."`);

      // Get the unified agent
      const agent = getAgent();
      if (!agent) {
        await ctx.reply('❌ Agent not initialized. Please restart.');
        return;
      }

      // Extract context from Telegram message
      const extractedContext = this.extractContext(ctx, userMessage);

      // Show typing indicator
      await ctx.sendChatAction('typing');

      // Process message through agent
      let fullResponse = '';
      let skillsUsed: string[] = [];
      let confidence = 0;

      try {
        // Use streaming if available
        const response = await agent.processMessage({
          userMessage,
          sessionId: `telegram-${userId}`,
          metadata: extractedContext,
          allowChaining: true,
        });

        fullResponse = response.content;
        skillsUsed = response.skillsUsed || [];
        confidence = response.confidence || 0;

        // Update session
        this.updateSession(userId);

        // Format and send response
        await this.sendResponse(ctx, {
          content: fullResponse,
          skillsUsed,
          confidence,
          duration: Date.now() - startTime,
        });
      } catch (error: any) {
        // Handle agent errors
        console.error('[Bridge] Agent error:', error);

        const fallbackResponse = this.getFallbackResponse(error);
        await ctx.reply(fallbackResponse, { parse_mode: 'Markdown' });

        this.emit('error', { userId, error, userMessage });
      }

      this.emit('message_processed', {
        userId,
        userMessage,
        response: fullResponse,
        skillsUsed,
        confidence,
        duration: Date.now() - startTime,
      });
    } catch (error) {
      console.error('[Bridge] Processing failed:', error);
      await ctx.reply('❌ Failed to process message. Please try again.').catch(console.error);
      this.emit('error', { userId, error });
    }
  }

  /**
   * Extract context from Telegram message
   */
  private extractContext(ctx: Context, userMessage: string) {
    const from = ctx.from;
    const message = ctx.message;

    return {
      source: 'telegram',
      userId: from?.id,
      username: from?.username,
      firstName: from?.first_name,
      lastName: from?.last_name,
      messageId: message?.message_id,
      timestamp: (message?.date || 0) * 1000,
      isBot: from?.is_bot || false,
      messageLength: userMessage.length,
      hasReply: message?.reply_to_message ? true : false,
      replyToUser: message?.reply_to_message?.from?.username,
    };
  }

  /**
   * Send formatted response to Telegram
   */
  private async sendResponse(
    ctx: Context,
    response: {
      content: string;
      skillsUsed: string[];
      confidence: number;
      duration: number;
    }
  ): Promise<void> {
    try {
      // Split long messages (Telegram limit is 4096 chars)
      const maxLength = 4000;
      const chunks = this.splitMessage(response.content, maxLength);

      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const isLast = i === chunks.length - 1;

        let messageText = chunk;

        // Add metadata to last chunk
        if (isLast && response.skillsUsed.length > 0) {
          const metadata = `\n\n📊 *Processing Info:*\n` +
            `• Skills: ${response.skillsUsed.join(', ')}\n` +
            `• Confidence: ${(response.confidence * 100).toFixed(0)}%\n` +
            `• Time: ${response.duration}ms`;

          messageText += metadata;
        }

        await ctx.reply(messageText, {
          parse_mode: 'Markdown',
          disable_web_page_preview: true,
        });
      }
    } catch (error) {
      console.error('[Bridge] Failed to send response:', error);
      await ctx.reply('❌ Failed to send response.').catch(console.error);
    }
  }

  /**
   * Split long message into chunks
   */
  private splitMessage(message: string, maxLength: number): string[] {
    if (message.length <= maxLength) {
      return [message];
    }

    const chunks: string[] = [];
    let current = '';

    const lines = message.split('\n');
    for (const line of lines) {
      if ((current + line + '\n').length > maxLength) {
        if (current) chunks.push(current.trim());
        current = line + '\n';
      } else {
        current += line + '\n';
      }
    }

    if (current) chunks.push(current.trim());
    return chunks;
  }

  /**
   * Get fallback response for errors
   */
  private getFallbackResponse(error: any): string {
    const errorType = error.code || error.name || 'Unknown';

    if (error.code === 'ECONNREFUSED' || error.message?.includes('ECONNREFUSED')) {
      return '🔴 *Connection Error*\n\nOllama is not responding. Make sure it\'s running:\n`ollama serve`';
    }

    if (error.message?.includes('timeout')) {
      return '⏱️ *Timeout Error*\n\nThe request took too long. Try a simpler task or check your internet connection.';
    }

    if (error.message?.includes('memory') || error.message?.includes('out of')) {
      return '💾 *Memory Error*\n\nThe system ran out of memory. Try a smaller task or restart Ollama.';
    }

    if (error.message?.includes('not found')) {
      return `❓ *Model Not Found*\n\nTrying to find the model... If this persists, run:\n\`ollama pull ${process.env.OLLAMA_MODEL || 'qwen2.5-coder:7b'}\``;
    }

    return `❌ *Error*\n\nType: ${errorType}\n\nTry again or check the logs.`;
  }

  /**
   * Get or create user session
   */
  private getOrCreateSession(userId: number, from: any): TelegramUserSession {
    let session = this.userSessions.get(userId);

    if (!session) {
      session = {
        userId,
        username: from?.username,
        firstName: from?.first_name,
        lastName: from?.last_name,
        createdAt: Date.now(),
        lastMessageAt: Date.now(),
        messageCount: 0,
      };
      this.userSessions.set(userId, session);
      console.log(`[Bridge] Created new session for user ${userId}`);
    }

    return session;
  }

  /**
   * Update session on message
   */
  private updateSession(userId: number): void {
    const session = this.userSessions.get(userId);
    if (session) {
      session.lastMessageAt = Date.now();
      session.messageCount++;
    }
  }

  /**
   * Get user session info
   */
  getSessionInfo(userId: number): TelegramUserSession | undefined {
    return this.userSessions.get(userId);
  }

  /**
   * Get bridge statistics
   */
  getStats(): {
    activeSessions: number;
    totalUsers: number;
    queuedMessages: number;
    processingUsers: number;
    agentReady: boolean;
  } {
    let queuedMessages = 0;
    let processingUsers = 0;

    for (const [userId, queue] of this.messageQueue) {
      queuedMessages += queue.length;
    }

    for (const [, isProcessing] of this.processing) {
      if (isProcessing) processingUsers++;
    }

    return {
      activeSessions: this.userSessions.size,
      totalUsers: this.userSessions.size,
      queuedMessages,
      processingUsers,
      agentReady: this.agentReady,
    };
  }

  /**
   * Clear stale sessions
   */
  async clearStaleSessions(): Promise<number> {
    const now = Date.now();
    let cleared = 0;

    for (const [userId, session] of this.userSessions) {
      if (now - session.lastMessageAt > this.config.sessionTimeout) {
        this.userSessions.delete(userId);
        this.messageQueue.delete(userId);
        this.processing.delete(userId);
        cleared++;
      }
    }

    if (cleared > 0) {
      console.log(`[Bridge] Cleared ${cleared} stale sessions`);
    }

    return cleared;
  }

  /**
   * Shutdown bridge gracefully
   */
  async shutdown(): Promise<void> {
    try {
      console.log('[Bridge] Shutting down TelegramAgentBridge...');

      // Wait for all queues to be processed
      let maxWait = 30000; // 30 seconds
      const checkInterval = 100;
      const startTime = Date.now();

      while (maxWait > 0) {
        let hasQueued = false;
        for (const queue of this.messageQueue.values()) {
          if (queue.length > 0) {
            hasQueued = true;
            break;
          }
        }

        if (!hasQueued) break;

        await new Promise(resolve => setTimeout(resolve, checkInterval));
        maxWait -= checkInterval;
      }

      // Shutdown agent
      await shutdownAgent();

      this.agentReady = false;
      this.userSessions.clear();
      this.messageQueue.clear();
      this.processing.clear();

      console.log('[Bridge] ✅ TelegramAgentBridge shutdown complete');
      this.emit('shutdown');
    } catch (error) {
      console.error('[Bridge] Shutdown error:', error);
      this.emit('error', error);
    }
  }
}

/**
 * Create and manage singleton bridge instance
 */
let bridgeInstance: TelegramAgentBridge | null = null;

export async function initializeBridge(config?: Partial<BridgeConfig>): Promise<TelegramAgentBridge> {
  if (bridgeInstance) {
    return bridgeInstance;
  }

  bridgeInstance = new TelegramAgentBridge(config);
  await bridgeInstance.initialize();
  return bridgeInstance;
}

export function getBridge(): TelegramAgentBridge | null {
  return bridgeInstance;
}

export async function shutdownBridge(): Promise<void> {
  if (bridgeInstance) {
    await bridgeInstance.shutdown();
    bridgeInstance = null;
  }
}
