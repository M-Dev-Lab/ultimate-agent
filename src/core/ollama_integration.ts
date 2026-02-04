/**
 * Comprehensive Ollama Integration
 * Handles proper API communication, response streaming, and error recovery
 * 
 * Based on Ollama API v1 documentation (2025)
 * Supports: chat completion, embeddings, model management
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';

// ============= TYPES & INTERFACES =============

export interface OllamaConfig {
  baseURL: string;
  model: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
  streamTimeout: number;
  keepAlive: string;
  contextLength?: number;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  images?: string[];
  toolName?: string;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  function: {
    name: string;
    arguments: Record<string, any>;
  };
}

export interface ChatRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  format?: 'json' | Record<string, any>;
  options?: Record<string, any>;
  keep_alive?: string;
}

export interface ChatResponse {
  model: string;
  created_at: string;
  message: {
    role: string;
    content: string;
    toolCalls?: ToolCall[];
  };
  done: boolean;
  done_reason?: string;
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
}

export interface StreamChunk {
  model: string;
  created_at: string;
  message: {
    role: string;
    content: string;
  };
  done: boolean;
}

export interface ModelInfo {
  name: string;
  model: string;
  modified_at: string;
  size: number;
  digest: string;
  details?: {
    parent_model: string;
    format: string;
    family: string;
    parameter_size: string;
    quantization_level: string;
  };
}

export interface EmbeddingRequest {
  model: string;
  input: string | string[];
  keep_alive?: string;
}

export interface EmbeddingResponse {
  model: string;
  embeddings: number[][];
  total_duration: number;
  load_duration: number;
  prompt_eval_count: number;
}

export interface OllamaError extends Error {
  status?: number;
  code?: string;
  retryable?: boolean;
}

// ============= OLLAMA CLIENT =============

export class OllamaClient extends EventEmitter {
  private client: AxiosInstance;
  private config: OllamaConfig;
  private retryQueue: Map<string, number> = new Map();
  private requestCache: Map<string, { data: any; timestamp: number }> = new Map();
  private cacheTimeout: number = 5 * 60 * 1000; // 5 minutes
  private requestLog: Array<{
    timestamp: number;
    endpoint: string;
    status: number;
    duration: number;
  }> = [];

  constructor(config: Partial<OllamaConfig> = {}) {
    super();
    
    this.config = {
      baseURL: config.baseURL || process.env.OLLAMA_BASE_URL || 'http://localhost:11434',
      model: config.model || process.env.OLLAMA_MODEL || 'llama2',
      timeout: config.timeout || 60000,
      retryAttempts: config.retryAttempts || 3,
      retryDelay: config.retryDelay || 1000,
      streamTimeout: config.streamTimeout || 300000,
      keepAlive: config.keepAlive || '5m',
      contextLength: config.contextLength || 4096
    };

    // Initialize axios client with proper error handling
    this.client = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      error => this.handleError(error)
    );

    console.log(`✓ Ollama client initialized: ${this.config.baseURL}/api`);
  }

  // ============= PUBLIC CHAT METHODS =============

  /**
   * Send a chat message and get a complete response
   * Non-streaming: waits for full response
   */
  async chat(
    messages: ChatMessage[],
    options?: Partial<ChatRequest>
  ): Promise<ChatResponse> {
    const cacheKey = this.generateCacheKey('chat', messages);
    
    // Check cache
    if (this.requestCache.has(cacheKey)) {
      const cached = this.requestCache.get(cacheKey)!;
      if (Date.now() - cached.timestamp < this.cacheTimeout) {
        console.log('📦 Serving from cache');
        return cached.data;
      }
    }

    const request: ChatRequest = {
      model: options?.model || this.config.model,
      messages,
      stream: false,
      keep_alive: this.config.keepAlive,
      ...options
    };

    try {
      const startTime = Date.now();
      const response = await this.retry(
        () => this.client.post<ChatResponse>('/api/chat', request),
        'chat'
      );

      const result = response.data;
      const duration = Date.now() - startTime;

      // Log request
      this.logRequest('/api/chat', 200, duration);

      // Cache result
      this.requestCache.set(cacheKey, { data: result, timestamp: Date.now() });

      // Emit analytics event
      this.emit('chatComplete', {
        model: result.model,
        tokens: (result.eval_count || 0) + (result.prompt_eval_count || 0),
        duration: duration,
        tokensPerSecond: result.eval_count && result.eval_duration 
          ? (result.eval_count / (result.eval_duration / 1e9))
          : 0
      });

      return result;
    } catch (error) {
      this.handleChatError(error as AxiosError);
      throw error;
    }
  }

  /**
   * Stream chat response for real-time updates
   */
  async *chatStream(
    messages: ChatMessage[],
    options?: Partial<ChatRequest>
  ): AsyncGenerator<string, void, unknown> {
    const request: ChatRequest = {
      model: options?.model || this.config.model,
      messages,
      stream: true,
      keep_alive: this.config.keepAlive,
      ...options
    };

    try {
      const response = await this.retry(
        () => this.client.post('/api/chat', request, {
          responseType: 'stream',
          timeout: this.config.streamTimeout
        }),
        'chatStream'
      );

      const startTime = Date.now();
      let totalTokens = 0;

      for await (const line of this.streamLines(response.data)) {
        if (!line.trim()) continue;

        try {
          const chunk = JSON.parse(line) as StreamChunk;
          
          // Yield content as it arrives
          if (chunk.message?.content) {
            yield chunk.message.content;
          }

          // Track final statistics
          if (chunk.done) {
            const duration = Date.now() - startTime;
            this.logRequest('/api/chat', 200, duration);
            
            this.emit('streamComplete', {
              model: chunk.model,
              duration,
              totalTokens
            });
          }
        } catch (parseError) {
          console.error('Failed to parse stream chunk:', parseError);
        }
      }
    } catch (error) {
      this.handleChatError(error as AxiosError);
      throw error;
    }
  }

  /**
   * Generate embeddings for text
   */
  async embed(input: string | string[]): Promise<number[][]> {
    const request: EmbeddingRequest = {
      model: this.config.model,
      input,
      keep_alive: this.config.keepAlive
    };

    try {
      const startTime = Date.now();
      const response = await this.retry(
        () => this.client.post<EmbeddingResponse>('/api/embed', request),
        'embed'
      );

      const duration = Date.now() - startTime;
      this.logRequest('/api/embed', 200, duration);

      this.emit('embedComplete', {
        model: response.data.model,
        inputCount: Array.isArray(input) ? input.length : 1,
        duration
      });

      return response.data.embeddings;
    } catch (error) {
      this.handleChatError(error as AxiosError);
      throw error;
    }
  }

  // ============= MODEL MANAGEMENT =============

  /**
   * List all available models
   */
  async listModels(): Promise<ModelInfo[]> {
    try {
      const response = await this.retry(
        () => this.client.get<{ models: ModelInfo[] }>('/api/tags'),
        'listModels'
      );
      return response.data.models || [];
    } catch (error) {
      console.error('Failed to list models:', error);
      return [];
    }
  }

  /**
   * Get information about a specific model
   */
  async getModelInfo(modelName: string): Promise<any> {
    try {
      const response = await this.retry(
        () => this.client.post('/api/show', { model: modelName }),
        'getModelInfo'
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to get info for model ${modelName}:`, error);
      return null;
    }
  }

  /**
   * Check if Ollama server is running
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/api/version', {
        timeout: 5000
      });
      const version = response.data?.version;
      console.log(`✓ Ollama healthy (v${version})`);
      return true;
    } catch (error) {
      console.error('✗ Ollama health check failed:', error);
      return false;
    }
  }

  // ============= PRIVATE HELPER METHODS =============

  /**
   * Retry logic with exponential backoff
   */
  private async retry<T>(
    fn: () => Promise<T>,
    operation: string,
    attempt: number = 1
  ): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      const err = error as OllamaError;
      const isRetryable = this.isRetryableError(err);

      if (isRetryable && attempt < this.config.retryAttempts) {
        const delay = this.config.retryDelay * Math.pow(2, attempt - 1);
        console.log(
          `⚠️  ${operation} failed (attempt ${attempt}), retrying in ${delay}ms...`
        );

        await new Promise(resolve => setTimeout(resolve, delay));
        return this.retry(fn, operation, attempt + 1);
      }

      throw error;
    }
  }

  /**
   * Determine if an error is retryable
   */
  private isRetryableError(error: OllamaError): boolean {
    // Network errors, timeouts, and 5xx errors are retryable
    return (
      !error.response ||
      (error.response.status >= 500 && error.response.status < 600) ||
      error.code === 'ECONNABORTED' ||
      error.code === 'ECONNREFUSED' ||
      error.code === 'ETIMEDOUT'
    );
  }

  /**
   * Handle axios errors and convert to OllamaError
   */
  private handleError(error: AxiosError): never {
    const ollamaError: OllamaError = new Error(
      error.message || 'Unknown Ollama error'
    );

    if (error.response) {
      ollamaError.status = error.response.status;
      ollamaError.message = (error.response.data as any)?.error || error.message;
    } else if (error.code) {
      ollamaError.code = error.code;
    }

    ollamaError.retryable = this.isRetryableError(ollamaError);
    throw ollamaError;
  }

  /**
   * Handle chat-specific errors with helpful messages
   */
  private handleChatError(error: AxiosError): void {
    if (error.code === 'ECONNREFUSED') {
      console.error(
        '❌ Cannot connect to Ollama. Make sure Ollama is running:\n' +
        '   ollama serve'
      );
    } else if (error.response?.status === 404) {
      console.error(
        '❌ Model not found. Make sure to pull it first:\n' +
        `   ollama pull ${this.config.model}`
      );
    } else if (error.response?.status === 503) {
      console.error('❌ Ollama server is temporarily unavailable');
    }
  }

  /**
   * Async generator to read stream lines
   */
  private async *streamLines(
    stream: NodeJS.ReadableStream
  ): AsyncGenerator<string, void, unknown> {
    let buffer = '';

    for await (const chunk of stream) {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        yield line;
      }
    }

    if (buffer) {
      yield buffer;
    }
  }

  /**
   * Generate cache key from chat messages
   */
  private generateCacheKey(operation: string, messages: ChatMessage[]): string {
    const hash = messages
      .map(m => `${m.role}:${m.content.substring(0, 50)}`)
      .join('|');
    return `${operation}:${hash}`;
  }

  /**
   * Log request metrics
   */
  private logRequest(endpoint: string, status: number, duration: number): void {
    this.requestLog.push({ timestamp: Date.now(), endpoint, status, duration });

    // Keep only last 1000 requests
    if (this.requestLog.length > 1000) {
      this.requestLog.shift();
    }
  }

  // ============= PUBLIC ANALYTICS =============

  /**
   * Get request statistics
   */
  getStats() {
    const totalDuration = this.requestLog.reduce((sum, r) => sum + r.duration, 0);
    const avgDuration = this.requestLog.length > 0 ? totalDuration / this.requestLog.length : 0;
    const maxDuration = Math.max(...this.requestLog.map(r => r.duration), 0);

    return {
      model: this.config.model,
      baseURL: this.config.baseURL,
      requestCount: this.requestLog.length,
      avgDuration: Math.round(avgDuration),
      maxDuration,
      cacheSize: this.requestCache.size,
      contextLength: this.config.contextLength,
      keepAlive: this.config.keepAlive
    };
  }

  /**
   * Clear caches and reset state
   */
  async reset(): Promise<void> {
    this.requestCache.clear();
    this.retryQueue.clear();
    this.requestLog = [];
    console.log('✓ Ollama client reset');
  }
}

// ============= SINGLETON INSTANCE =============

let instance: OllamaClient | null = null;

export function getOllamaClient(config?: Partial<OllamaConfig>): OllamaClient {
  if (!instance) {
    instance = new OllamaClient(config);
  }
  return instance;
}

export function resetOllamaClient(): void {
  instance = null;
}

export default OllamaClient;
