/**
 * Advanced Memory & State Management System
 * Handles conversation history, context preservation, and intelligent recall
 * 
 * Features:
 * - Conversation memory with semantic indexing
 * - Context sliding window
 * - Memory compression for long conversations
 * - Emotion/tone tracking
 * - Cross-session knowledge retention
 */

import { EventEmitter } from 'events';
import { ChatMessage } from './ollama_integration.js';
import * as fs from 'fs/promises';
import * as path from 'path';

// ============= TYPES =============

export interface MemoryEntry {
  id: string;
  timestamp: number;
  role: 'user' | 'assistant';
  content: string;
  embedding?: number[];
  metadata: {
    tokens: number;
    tone?: string;
    importance?: number;
    tags?: string[];
    relatedEntries?: string[];
  };
}

export interface ConversationState {
  sessionId: string;
  userId: string;
  startTime: number;
  lastUpdate: number;
  messageCount: number;
  memory: MemoryEntry[];
  context: {
    topic?: string;
    sentiment?: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
    goals?: string[];
  };
}

export interface MemoryConfig {
  maxMemorySize: number; // bytes
  contextWindow: number; // number of messages to keep in active context
  compressionThreshold: number; // when to compress old messages
  persistPath?: string;
  enableSemanticIndex: boolean;
}

// ============= MEMORY MANAGER =============

export class MemoryManager extends EventEmitter {
  private conversations: Map<string, ConversationState> = new Map();
  private semanticIndex: Map<string, number[]> = new Map();
  private config: MemoryConfig;
  private persistInterval: NodeJS.Timer | null = null;

  constructor(config: Partial<MemoryConfig> = {}) {
    super();

    this.config = {
      maxMemorySize: config.maxMemorySize || 10 * 1024 * 1024, // 10MB
      contextWindow: config.contextWindow || 50, // Last 50 messages
      compressionThreshold: config.compressionThreshold || 100,
      persistPath: config.persistPath || './memory/conversations',
      enableSemanticIndex: config.enableSemanticIndex !== false
    };

    this.initializePersistence();
    console.log('✓ Memory manager initialized');
  }

  // ============= SESSION MANAGEMENT =============

  /**
   * Create or get conversation session
   */
  getOrCreateSession(userId: string, sessionId?: string): ConversationState {
    const id = sessionId || `session_${userId}_${Date.now()}`;

    if (!this.conversations.has(id)) {
      this.conversations.set(id, {
        sessionId: id,
        userId,
        startTime: Date.now(),
        lastUpdate: Date.now(),
        messageCount: 0,
        memory: [],
        context: {}
      });

      console.log(`📝 Created new session: ${id}`);
      this.emit('sessionCreated', { sessionId: id, userId });
    }

    return this.conversations.get(id)!;
  }

  /**
   * Add message to conversation memory
   */
  addMessage(
    sessionId: string,
    role: 'user' | 'assistant',
    content: string,
    metadata?: Partial<MemoryEntry['metadata']>
  ): MemoryEntry {
    const session = this.conversations.get(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    const entry: MemoryEntry = {
      id: `msg_${Date.now()}_${Math.random()}`,
      timestamp: Date.now(),
      role,
      content,
      metadata: {
        tokens: this.estimateTokens(content),
        importance: this.calculateImportance(content),
        ...metadata
      }
    };

    session.memory.push(entry);
    session.messageCount++;
    session.lastUpdate = Date.now();

    // Index for semantic search
    if (this.config.enableSemanticIndex) {
      this.semanticIndex.set(entry.id, this.generateSimpleEmbedding(content));
    }

    // Auto-compress if needed
    if (session.memory.length >= this.config.compressionThreshold) {
      this.compressMemory(sessionId);
    }

    this.emit('messageAdded', { sessionId, entry });
    return entry;
  }

  /**
   * Get conversation context window
   */
  getContextWindow(sessionId: string, windowSize?: number): ChatMessage[] {
    const session = this.conversations.get(sessionId);
    if (!session) return [];

    const size = windowSize || this.config.contextWindow;
    const start = Math.max(0, session.memory.length - size);
    const messages: ChatMessage[] = [];

    for (let i = start; i < session.memory.length; i++) {
      const entry = session.memory[i];
      messages.push({
        role: entry.role === 'user' ? 'user' : 'assistant',
        content: entry.content
      });
    }

    return messages;
  }

  /**
   * Retrieve similar messages from history (semantic search)
   */
  retrieveSimilar(sessionId: string, query: string, limit: number = 5): MemoryEntry[] {
    const session = this.conversations.get(sessionId);
    if (!session) return [];

    const queryEmbedding = this.generateSimpleEmbedding(query);
    const scores: Array<{ entry: MemoryEntry; score: number }> = [];

    for (const entry of session.memory) {
      if (this.semanticIndex.has(entry.id)) {
        const entryEmbedding = this.semanticIndex.get(entry.id)!;
        const similarity = this.cosineSimilarity(queryEmbedding, entryEmbedding);
        scores.push({ entry, score: similarity });
      }
    }

    return scores
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map(s => s.entry);
  }

  /**
   * Update conversation context
   */
  updateContext(
    sessionId: string,
    context: Partial<ConversationState['context']>
  ): void {
    const session = this.conversations.get(sessionId);
    if (!session) return;

    session.context = { ...session.context, ...context };
    session.lastUpdate = Date.now();
  }

  /**
   * Get conversation summary
   */
  getSummary(sessionId: string): {
    duration: number;
    messageCount: number;
    lastMessage: string;
    topic?: string;
    sentiment?: string;
  } {
    const session = this.conversations.get(sessionId);
    if (!session) {
      return {
        duration: 0,
        messageCount: 0,
        lastMessage: ''
      };
    }

    return {
      duration: Date.now() - session.startTime,
      messageCount: session.messageCount,
      lastMessage: session.memory[session.memory.length - 1]?.content || '',
      topic: session.context.topic,
      sentiment: session.context.sentiment
    };
  }

  // ============= MEMORY MANAGEMENT =============

  /**
   * Compress old messages to free space
   */
  private compressMemory(sessionId: string): void {
    const session = this.conversations.get(sessionId);
    if (!session || session.memory.length < this.config.compressionThreshold) {
      return;
    }

    const keepCount = Math.floor(this.config.compressionThreshold * 0.7);
    const toCompress = session.memory.slice(0, session.memory.length - keepCount);

    // Create summary of compressed messages
    if (toCompress.length > 0) {
      const summaryContent = `[Compressed ${toCompress.length} earlier messages in conversation about: ${
        toCompress.map(m => m.content.substring(0, 20)).join(', ')
      }...]`;

      const summaryEntry: MemoryEntry = {
        id: `compressed_${Date.now()}`,
        timestamp: toCompress[0].timestamp,
        role: 'assistant',
        content: summaryContent,
        metadata: {
          tokens: summaryContent.length / 4,
          importance: 1
        }
      };

      // Replace compressed messages with summary
      session.memory = [summaryEntry, ...session.memory.slice(session.memory.length - keepCount)];
      console.log(`📦 Compressed ${toCompress.length} messages in session ${sessionId}`);
      this.emit('memoryCompressed', { sessionId, compressedCount: toCompress.length });
    }
  }

  /**
   * Clear old sessions
   */
  clearOldSessions(maxAge: number = 24 * 60 * 60 * 1000): void {
    let cleared = 0;
    const now = Date.now();

    for (const [sessionId, session] of this.conversations.entries()) {
      if (now - session.lastUpdate > maxAge) {
        this.conversations.delete(sessionId);
        cleared++;
      }
    }

    if (cleared > 0) {
      console.log(`🗑️  Cleared ${cleared} old sessions`);
      this.emit('sessionsCleaned', { count: cleared });
    }
  }

  /**
   * Export session to file
   */
  async exportSession(sessionId: string): Promise<string> {
    const session = this.conversations.get(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    const exportData = {
      ...session,
      exportedAt: new Date().toISOString(),
      memoryStats: {
        entries: session.memory.length,
        totalTokens: session.memory.reduce((sum, m) => sum + m.metadata.tokens, 0)
      }
    };

    const filename = `${sessionId}_${Date.now()}.json`;
    const filepath = path.join(this.config.persistPath || '.', filename);

    await fs.mkdir(path.dirname(filepath), { recursive: true });
    await fs.writeFile(filepath, JSON.stringify(exportData, null, 2));

    console.log(`✓ Session exported to: ${filepath}`);
    return filepath;
  }

  /**
   * Import session from file
   */
  async importSession(filepath: string): Promise<ConversationState> {
    const data = JSON.parse(await fs.readFile(filepath, 'utf-8'));
    const session = data as ConversationState;

    this.conversations.set(session.sessionId, session);

    // Rebuild semantic index
    if (this.config.enableSemanticIndex) {
      for (const entry of session.memory) {
        this.semanticIndex.set(entry.id, this.generateSimpleEmbedding(entry.content));
      }
    }

    console.log(`✓ Session imported: ${session.sessionId}`);
    return session;
  }

  // ============= PRIVATE HELPERS =============

  /**
   * Calculate message importance (0-10)
   */
  private calculateImportance(content: string): number {
    let importance = 5; // Default

    // Boost for questions
    if (content.includes('?')) importance += 2;

    // Boost for key coding terms
    if (/\b(critical|urgent|bug|error|fail|problem)\b/i.test(content)) {
      importance += 3;
    }

    // Boost for action items
    if (/\b(please|need|must|should|implement|create|fix)\b/i.test(content)) {
      importance += 1;
    }

    return Math.min(10, importance);
  }

  /**
   * Estimate tokens (approximation)
   */
  private estimateTokens(content: string): number {
    return Math.ceil(content.length / 4); // Rough estimate
  }

  /**
   * Generate simple embedding (word frequency vector)
   */
  private generateSimpleEmbedding(text: string): number[] {
    const words = text.toLowerCase().match(/\b\w+\b/g) || [];
    const embedding = new Array(100).fill(0);

    for (const word of words) {
      const hash = this.simpleHash(word);
      const index = hash % 100;
      embedding[index]++;
    }

    return embedding;
  }

  /**
   * Simple hash function
   */
  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  /**
   * Calculate cosine similarity between two embeddings
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < Math.min(a.length, b.length); i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    const denominator = Math.sqrt(normA) * Math.sqrt(normB);
    return denominator === 0 ? 0 : dotProduct / denominator;
  }

  /**
   * Initialize persistence
   */
  private initializePersistence(): void {
    if (!this.config.persistPath) return;

    // Auto-save every 5 minutes
    this.persistInterval = setInterval(() => {
      this.persistAllSessions().catch(err => {
        console.error('Error persisting sessions:', err);
      });
    }, 5 * 60 * 1000);
  }

  /**
   * Persist all sessions to disk
   */
  private async persistAllSessions(): Promise<void> {
    const dirPath = this.config.persistPath || '.';

    for (const [sessionId, session] of this.conversations.entries()) {
      try {
        const filepath = path.join(dirPath, `${sessionId}.json`);
        await fs.mkdir(dirPath, { recursive: true });
        await fs.writeFile(filepath, JSON.stringify(session, null, 2));
      } catch (error) {
        console.error(`Error persisting session ${sessionId}:`, error);
      }
    }
  }

  // ============= PUBLIC ANALYTICS =============

  /**
   * Get memory statistics
   */
  getStats() {
    let totalMessages = 0;
    let totalTokens = 0;
    let oldestSession = Date.now();

    for (const session of this.conversations.values()) {
      totalMessages += session.memory.length;
      totalTokens += session.memory.reduce((sum, m) => sum + m.metadata.tokens, 0);
      oldestSession = Math.min(oldestSession, session.startTime);
    }

    return {
      sessionCount: this.conversations.size,
      totalMessages,
      totalTokens,
      memorySize: Math.round(totalTokens * 4 / 1024), // KB estimate
      oldestSession: new Date(oldestSession).toISOString(),
      maxMemory: Math.round(this.config.maxMemorySize / 1024 / 1024) // MB
    };
  }

  /**
   * Cleanup and shutdown
   */
  async shutdown(): Promise<void> {
    if (this.persistInterval) {
      clearInterval(this.persistInterval);
    }

    await this.persistAllSessions();
    console.log('✓ Memory manager shutdown');
  }
}

export default MemoryManager;
