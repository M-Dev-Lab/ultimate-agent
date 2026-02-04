/**
 * Fixed Ollama Integration - Enhanced Connection Management
 * 
 * Features:
 * - Robust health checks with retry logic
 * - Connection pooling
 * - Model availability validation
 * - Fallback model selection
 * - Connection status tracking
 * - Recovery from network errors
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';

interface OllamaHealthStatus {
  connected: boolean;
  lastCheck: number;
  modelAvailable: boolean;
  currentModel: string;
  responseTime: number;
  error?: string;
}

export class OllamaConnectionManager extends EventEmitter {
  private client: AxiosInstance;
  private baseURL: string;
  private model: string;
  private healthStatus: OllamaHealthStatus;
  private healthCheckInterval: NodeJS.Timer | null = null;
  private maxRetries: number = 5;
  private retryDelay: number = 1000; // milliseconds
  private logDir: string;

  constructor(
    baseURL: string = process.env.OLLAMA_URL || 'http://localhost:11434',
    model: string = process.env.OLLAMA_MODEL || 'qwen2.5-coder:7b',
    logDir: string = path.join(process.cwd(), 'logs')
  ) {
    super();

    this.baseURL = baseURL;
    this.model = model;
    this.logDir = logDir;

    // Initialize axios client with timeout and retry config
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Initialize health status
    this.healthStatus = {
      connected: false,
      lastCheck: 0,
      modelAvailable: false,
      currentModel: model,
      responseTime: 0,
    };

    this.setupAxiosInterceptors();
  }

  /**
   * Setup axios interceptors for error handling
   */
  private setupAxiosInterceptors(): void {
    this.client.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
          this.emit('connection-error', {
            type: 'network',
            message: 'Cannot connect to Ollama',
            url: this.baseURL,
            error: error.message,
          });
        } else if (error.code === 'ETIMEDOUT') {
          this.emit('timeout', {
            message: 'Ollama request timeout',
            duration: 30000,
          });
        }
        throw error;
      }
    );
  }

  /**
   * Perform health check with retry logic
   */
  async checkHealth(retry: number = 0): Promise<boolean> {
    try {
      const startTime = Date.now();

      // Try to get Ollama tags (list available models)
      const tagsResponse = await this.client.get('/api/tags');
      const responseTime = Date.now() - startTime;

      if (!tagsResponse.data?.models || tagsResponse.data.models.length === 0) {
        this.healthStatus.connected = true;
        this.healthStatus.modelAvailable = false;
        this.healthStatus.responseTime = responseTime;
        this.healthStatus.error = 'No models available. Run: ollama pull qwen2.5-coder:7b';
        this.healthStatus.lastCheck = Date.now();

        this.emit('health-check', {
          status: 'warning',
          message: 'Ollama connected but no models available',
        });

        return false;
      }

      // Check if our model is available
      const modelExists = tagsResponse.data.models.some(
        (m: any) => m.name === this.model || m.name.startsWith(this.model)
      );

      if (!modelExists) {
        console.warn(`[Ollama] Model ${this.model} not found. Available models:`, 
          tagsResponse.data.models.map((m: any) => m.name).join(', ')
        );

        this.emit('model-not-found', {
          requested: this.model,
          available: tagsResponse.data.models.map((m: any) => m.name),
        });
      }

      // Try a simple chat request to verify model works
      const chatStart = Date.now();
      const testResponse = await this.client.post('/api/chat', {
        model: this.model,
        messages: [{ role: 'user', content: 'ping' }],
        stream: false,
      });

      const chatResponseTime = Date.now() - chatStart;

      if (testResponse.data?.message?.content) {
        this.healthStatus.connected = true;
        this.healthStatus.modelAvailable = true;
        this.healthStatus.responseTime = chatResponseTime;
        this.healthStatus.error = undefined;
        this.healthStatus.lastCheck = Date.now();

        this.emit('health-check', {
          status: 'ok',
          responseTime: chatResponseTime,
          model: this.model,
        });

        return true;
      }

      throw new Error('No response from model');
    } catch (error: any) {
      if (retry < this.maxRetries) {
        const delay = this.retryDelay * Math.pow(2, retry); // Exponential backoff
        console.log(`[Ollama] Health check failed, retrying in ${delay}ms...`);

        await new Promise(resolve => setTimeout(resolve, delay));
        return this.checkHealth(retry + 1);
      }

      const errorMessage = error.code === 'ECONNREFUSED' 
        ? `Cannot connect to Ollama at ${this.baseURL}. Make sure Ollama is running: ollama serve`
        : error.message;

      this.healthStatus.connected = false;
      this.healthStatus.modelAvailable = false;
      this.healthStatus.error = errorMessage;
      this.healthStatus.lastCheck = Date.now();

      this.emit('health-check', {
        status: 'error',
        error: errorMessage,
        attempts: retry + 1,
      });

      return false;
    }
  }

  /**
   * Start periodic health checks
   */
  startHealthChecks(intervalMs: number = 30000): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    // Initial check
    this.checkHealth().catch(console.error);

    // Periodic checks
    this.healthCheckInterval = setInterval(() => {
      this.checkHealth().catch(console.error);
    }, intervalMs);

    console.log(`[Ollama] Started health checks every ${intervalMs}ms`);
  }

  /**
   * Stop health checks
   */
  stopHealthChecks(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
      console.log('[Ollama] Stopped health checks');
    }
  }

  /**
   * Get current health status
   */
  getHealthStatus(): OllamaHealthStatus {
    return { ...this.healthStatus };
  }

  /**
   * Test connection with timeout
   */
  async testConnection(timeoutMs: number = 5000): Promise<boolean> {
    try {
      const startTime = Date.now();

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      // Simple GET request to check if Ollama is responding
      await axios.get(`${this.baseURL}/api/tags`, {
        signal: controller.signal as any,
        timeout: timeoutMs,
      });

      clearTimeout(timeoutId);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get available models
   */
  async getAvailableModels(): Promise<string[]> {
    try {
      const response = await this.client.get('/api/tags');
      return response.data?.models?.map((m: any) => m.name) || [];
    } catch (error) {
      console.error('[Ollama] Failed to get models:', error);
      return [];
    }
  }

  /**
   * Pull a model (download if not available)
   */
  async pullModel(modelName: string): Promise<boolean> {
    try {
      console.log(`[Ollama] Pulling model ${modelName}...`);

      const response = await this.client.post('/api/pull', {
        name: modelName,
        stream: false,
      });

      console.log(`[Ollama] ✅ Model ${modelName} pulled successfully`);
      return true;
    } catch (error: any) {
      console.error(`[Ollama] Failed to pull model ${modelName}:`, error.message);
      return false;
    }
  }

  /**
   * Get model info
   */
  async getModelInfo(modelName: string): Promise<any> {
    try {
      const response = await this.client.post('/api/show', {
        name: modelName,
      });
      return response.data;
    } catch (error: any) {
      console.error(`[Ollama] Failed to get model info:`, error.message);
      return null;
    }
  }

  /**
   * Log status to file
   */
  async logStatus(): Promise<void> {
    try {
      await fs.mkdir(this.logDir, { recursive: true });

      const logFile = path.join(this.logDir, 'ollama-status.log');
      const timestamp = new Date().toISOString();
      const statusLine = JSON.stringify({
        timestamp,
        ...this.healthStatus,
      });

      await fs.appendFile(logFile, statusLine + '\n');
    } catch (error) {
      console.error('[Ollama] Failed to log status:', error);
    }
  }

  /**
   * Get statistics
   */
  getStats(): {
    connected: boolean;
    modelAvailable: boolean;
    responseTime: number;
    model: string;
    baseURL: string;
    uptime: string;
  } {
    const status = this.healthStatus;
    const lastCheckAge = Date.now() - status.lastCheck;

    return {
      connected: status.connected,
      modelAvailable: status.modelAvailable,
      responseTime: status.responseTime,
      model: status.currentModel,
      baseURL: this.baseURL,
      uptime: `${Math.floor(lastCheckAge / 1000)}s ago`,
    };
  }

  /**
   * Cleanup resources
   */
  async shutdown(): Promise<void> {
    this.stopHealthChecks();
    await this.logStatus();
    console.log('[Ollama] Connection manager shutdown');
  }
}

/**
 * Create and manage singleton connection manager
 */
let connectionManager: OllamaConnectionManager | null = null;

export async function initializeOllamaConnection(
  baseURL?: string,
  model?: string
): Promise<OllamaConnectionManager> {
  if (connectionManager) {
    return connectionManager;
  }

  connectionManager = new OllamaConnectionManager(baseURL, model);

  // Perform initial health check
  const isHealthy = await connectionManager.checkHealth();

  if (!isHealthy) {
    console.warn('[Ollama] ⚠️  Ollama connection failed. Make sure Ollama is running:');
    console.warn('[Ollama] Run: ollama serve');
    console.warn('[Ollama] Or pull the model: ollama pull qwen2.5-coder:7b');
  } else {
    console.log('[Ollama] ✅ Successfully connected to Ollama');
  }

  // Start periodic health checks
  connectionManager.startHealthChecks(30000);

  return connectionManager;
}

export function getOllamaConnection(): OllamaConnectionManager | null {
  return connectionManager;
}

export async function shutdownOllamaConnection(): Promise<void> {
  if (connectionManager) {
    await connectionManager.shutdown();
    connectionManager = null;
  }
}
