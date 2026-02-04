/**
 * Telegram Memory Persistence Manager
 * 
 * Features:
 * - Per-user conversation history
 * - Context window management
 * - Automatic persistence to disk
 * - Memory compression and archival
 * - Fast retrieval and recall
 * - Token counting and limits
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { EventEmitter } from 'events';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  tokens?: number;
  metadata?: Record<string, any>;
}

interface ConversationSession {
  userId: number;
  username?: string;
  createdAt: number;
  lastUpdated: number;
  messageCount: number;
  totalTokens: number;
  messages: Message[];
  archived: ArchivedSegment[];
}

interface ArchivedSegment {
  id: string;
  startTime: number;
  endTime: number;
  summary: string;
  messageCount: number;
  tokens: number;
}

export class TelegramMemoryManager extends EventEmitter {
  private sessions: Map<number, ConversationSession> = new Map();
  private dataDir: string;
  private contextWindowSize: number = 50; // messages
  private maxTokensPerSession: number = 4000; // for context
  private compressionThreshold: number = 100; // messages
  private autoPersistInterval: number = 60000; // 1 minute
  private persistTimer: NodeJS.Timer | null = null;

  constructor(dataDir: string = path.join(process.cwd(), 'data', 'telegram-memory')) {
    super();
    this.dataDir = dataDir;
  }

  /**
   * Initialize memory manager
   */
  async initialize(): Promise<void> {
    try {
      // Create data directories
      await fs.mkdir(this.dataDir, { recursive: true });
      await fs.mkdir(path.join(this.dataDir, 'conversations'), { recursive: true });
      await fs.mkdir(path.join(this.dataDir, 'archives'), { recursive: true });

      console.log('[Memory] Initialized memory manager');

      // Start auto-persistence
      this.startAutoPersist();

      this.emit('ready');
    } catch (error) {
      console.error('[Memory] Initialization error:', error);
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Get or create conversation session
   */
  async getOrCreateSession(userId: number, username?: string): Promise<ConversationSession> {
    if (this.sessions.has(userId)) {
      return this.sessions.get(userId)!;
    }

    // Try to load from disk
    const session = await this.loadSessionFromDisk(userId);
    if (session) {
      this.sessions.set(userId, session);
      return session;
    }

    // Create new session
    const newSession: ConversationSession = {
      userId,
      username,
      createdAt: Date.now(),
      lastUpdated: Date.now(),
      messageCount: 0,
      totalTokens: 0,
      messages: [],
      archived: [],
    };

    this.sessions.set(userId, newSession);
    return newSession;
  }

  /**
   * Add message to conversation
   */
  async addMessage(
    userId: number,
    role: 'user' | 'assistant',
    content: string,
    metadata?: Record<string, any>
  ): Promise<Message> {
    const session = await this.getOrCreateSession(userId);

    const tokens = this.estimateTokens(content);
    const message: Message = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role,
      content,
      timestamp: Date.now(),
      tokens,
      metadata,
    };

    session.messages.push(message);
    session.messageCount++;
    session.totalTokens += tokens;
    session.lastUpdated = Date.now();

    // Check if compression is needed
    if (session.messages.length > this.compressionThreshold) {
      await this.compressOldMessages(userId);
    }

    // Check if total tokens exceed limit
    if (session.totalTokens > this.maxTokensPerSession) {
      await this.pruneOldMessages(userId);
    }

    this.emit('message_added', {
      userId,
      role,
      tokens,
      sessionMessageCount: session.messages.length,
    });

    return message;
  }

  /**
   * Get context window for message processing
   */
  getContextWindow(userId: number): Message[] {
    const session = this.sessions.get(userId);
    if (!session) {
      return [];
    }

    // Get last N messages, up to context window size
    const startIdx = Math.max(0, session.messages.length - this.contextWindowSize);
    return session.messages.slice(startIdx);
  }

  /**
   * Get conversation formatted for LLM
   */
  getConversationForLLM(userId: number): Array<{ role: string; content: string }> {
    const messages = this.getContextWindow(userId);
    return messages.map(m => ({
      role: m.role,
      content: m.content,
    }));
  }

  /**
   * Search conversation history
   */
  async searchConversation(
    userId: number,
    query: string,
    limit: number = 10
  ): Promise<Message[]> {
    const session = this.sessions.get(userId);
    if (!session) {
      return [];
    }

    const queryLower = query.toLowerCase();
    const results = session.messages.filter(m =>
      m.content.toLowerCase().includes(queryLower)
    );

    return results.slice(-limit);
  }

  /**
   * Compress old messages into summary
   */
  private async compressOldMessages(userId: number): Promise<void> {
    const session = await this.getOrCreateSession(userId);

    if (session.messages.length < this.compressionThreshold) {
      return;
    }

    // Keep last 70% of threshold
    const keepCount = Math.floor(this.compressionThreshold * 0.7);
    const compressCount = session.messages.length - keepCount;

    if (compressCount <= 0) {
      return;
    }

    const messagesToCompress = session.messages.slice(0, compressCount);
    const messagesToKeep = session.messages.slice(compressCount);

    // Create summary of compressed messages
    const summary = this.createMessageSummary(messagesToCompress);
    const tokens = messagesToCompress.reduce((sum, m) => sum + (m.tokens || 0), 0);

    // Create archived segment
    const archived: ArchivedSegment = {
      id: `archive-${Date.now()}`,
      startTime: messagesToCompress[0]?.timestamp || 0,
      endTime: messagesToCompress[messagesToCompress.length - 1]?.timestamp || 0,
      summary,
      messageCount: compressCount,
      tokens,
    };

    session.archived.push(archived);
    session.messages = messagesToKeep;
    session.lastUpdated = Date.now();

    this.emit('messages_compressed', {
      userId,
      compressedCount: compressCount,
      newMessageCount: session.messages.length,
      archiveCount: session.archived.length,
    });

    console.log(`[Memory] Compressed ${compressCount} old messages for user ${userId}`);
  }

  /**
   * Prune old messages if token limit exceeded
   */
  private async pruneOldMessages(userId: number): Promise<void> {
    const session = await this.getOrCreateSession(userId);

    // Remove oldest messages until under limit
    let totalTokens = session.totalTokens;
    while (session.messages.length > 10 && totalTokens > this.maxTokensPerSession) {
      const removed = session.messages.shift();
      if (removed) {
        totalTokens -= removed.tokens || 0;
      }
    }

    session.totalTokens = totalTokens;
    session.lastUpdated = Date.now();

    this.emit('messages_pruned', {
      userId,
      newMessageCount: session.messages.length,
      totalTokens,
    });
  }

  /**
   * Create summary of messages
   */
  private createMessageSummary(messages: Message[]): string {
    const topics = new Set<string>();
    const keywords = new Map<string, number>();

    for (const msg of messages) {
      const words = msg.content.toLowerCase().split(/\s+/);
      for (const word of words) {
        if (word.length > 4) {
          keywords.set(word, (keywords.get(word) || 0) + 1);
        }
      }
    }

    const topKeywords = Array.from(keywords.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([word]) => word);

    const timeRange = messages.length > 0
      ? ` from ${new Date(messages[0].timestamp).toLocaleDateString()} to ${new Date(messages[messages.length - 1].timestamp).toLocaleDateString()}`
      : '';

    return `Earlier conversation${timeRange} discussing: ${topKeywords.join(', ')}`;
  }

  /**
   * Estimate tokens in text (simplified)
   */
  private estimateTokens(text: string): number {
    // Rough estimate: 1 token per 4 characters
    return Math.ceil(text.length / 4);
  }

  /**
   * Persist session to disk
   */
  async persistSession(userId: number): Promise<void> {
    const session = this.sessions.get(userId);
    if (!session) {
      return;
    }

    try {
      const filePath = path.join(this.dataDir, 'conversations', `${userId}.json`);
      await fs.writeFile(filePath, JSON.stringify(session, null, 2));

      this.emit('session_persisted', { userId, messageCount: session.messageCount });
    } catch (error) {
      console.error(`[Memory] Failed to persist session ${userId}:`, error);
      this.emit('error', error);
    }
  }

  /**
   * Load session from disk
   */
  private async loadSessionFromDisk(userId: number): Promise<ConversationSession | null> {
    try {
      const filePath = path.join(this.dataDir, 'conversations', `${userId}.json`);
      const data = await fs.readFile(filePath, 'utf-8');
      const session = JSON.parse(data) as ConversationSession;

      console.log(`[Memory] Loaded session for user ${userId} with ${session.messageCount} messages`);
      return session;
    } catch (error) {
      if ((error as any).code !== 'ENOENT') {
        console.error(`[Memory] Failed to load session ${userId}:`, error);
      }
      return null;
    }
  }

  /**
   * Start auto-persistence
   */
  private startAutoPersist(): void {
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
    }

    this.persistTimer = setInterval(async () => {
      for (const userId of this.sessions.keys()) {
        await this.persistSession(userId);
      }
    }, this.autoPersistInterval);
  }

  /**
   * Get session statistics
   */
  getSessionStats(userId: number): {
    messageCount: number;
    totalTokens: number;
    contextWindowSize: number;
    archiveCount: number;
    createdAt: number;
    lastUpdated: number;
  } | null {
    const session = this.sessions.get(userId);
    if (!session) {
      return null;
    }

    return {
      messageCount: session.messageCount,
      totalTokens: session.totalTokens,
      contextWindowSize: session.messages.length,
      archiveCount: session.archived.length,
      createdAt: session.createdAt,
      lastUpdated: session.lastUpdated,
    };
  }

  /**
   * Clear session
   */
  async clearSession(userId: number): Promise<void> {
    this.sessions.delete(userId);

    try {
      const filePath = path.join(this.dataDir, 'conversations', `${userId}.json`);
      await fs.unlink(filePath);
    } catch (error) {
      // File might not exist
    }

    this.emit('session_cleared', { userId });
  }

  /**
   * Export conversation
   */
  async exportConversation(userId: number): Promise<string> {
    const session = this.sessions.get(userId);
    if (!session) {
      return '';
    }

    const lines: string[] = [
      `# Conversation Export for User ${userId}`,
      `Date: ${new Date().toISOString()}`,
      `Total Messages: ${session.messageCount}`,
      `Total Tokens: ${session.totalTokens}`,
      '',
    ];

    for (const archive of session.archived) {
      lines.push(`## Archive: ${archive.summary}`);
      lines.push(`(${archive.messageCount} messages, ${archive.tokens} tokens)`);
      lines.push('');
    }

    lines.push('## Recent Messages');
    for (const msg of session.messages) {
      lines.push(`\n**${msg.role.toUpperCase()}** (${new Date(msg.timestamp).toLocaleString()}):`);
      lines.push(msg.content);
    }

    return lines.join('\n');
  }

  /**
   * Get manager statistics
   */
  getStats(): {
    activeSessions: number;
    totalMessages: number;
    totalTokens: number;
    totalArchives: number;
  } {
    let totalMessages = 0;
    let totalTokens = 0;
    let totalArchives = 0;

    for (const session of this.sessions.values()) {
      totalMessages += session.messageCount;
      totalTokens += session.totalTokens;
      totalArchives += session.archived.length;
    }

    return {
      activeSessions: this.sessions.size,
      totalMessages,
      totalTokens,
      totalArchives,
    };
  }

  /**
   * Shutdown memory manager
   */
  async shutdown(): Promise<void> {
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
    }

    // Persist all sessions
    for (const userId of this.sessions.keys()) {
      await this.persistSession(userId);
    }

    console.log('[Memory] Memory manager shutdown');
  }
}

/**
 * Singleton memory manager
 */
let memoryManagerInstance: TelegramMemoryManager | null = null;

export async function initializeMemoryManager(
  dataDir?: string
): Promise<TelegramMemoryManager> {
  if (memoryManagerInstance) {
    return memoryManagerInstance;
  }

  memoryManagerInstance = new TelegramMemoryManager(dataDir);
  await memoryManagerInstance.initialize();
  return memoryManagerInstance;
}

export function getMemoryManager(): TelegramMemoryManager | null {
  return memoryManagerInstance;
}

export async function shutdownMemoryManager(): Promise<void> {
  if (memoryManagerInstance) {
    await memoryManagerInstance.shutdown();
    memoryManagerInstance = null;
  }
}
