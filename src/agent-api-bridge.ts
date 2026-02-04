/**
 * Telegram Bot - Python Agent Bridge
 * 
 * Connects Telegram bot buttons and commands to Python agent API endpoints
 * Running on http://localhost:8000
 */

import axios, { AxiosInstance } from 'axios';
import { Context } from 'telegraf';

const AGENT_API_BASE = process.env.AGENT_API_URL || 'http://localhost:8000/api';
const REQUEST_TIMEOUT = 30000; // 30 seconds

export class AgentAPI {
  private client: AxiosInstance;
  private isOnline: boolean = false;
  private lastHealthCheck: number = 0;

  constructor() {
    this.client = axios.create({
      baseURL: AGENT_API_BASE,
      timeout: REQUEST_TIMEOUT,
      validateStatus: () => true, // Don't throw on any status code
    });
  }

  /**
   * Check if agent is online
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      this.isOnline = response.status === 200;
      this.lastHealthCheck = Date.now();
      return this.isOnline;
    } catch (error) {
      this.isOnline = false;
      return false;
    }
  }

  /**
   * Execute build command
   */
  async executeBuild(request: string, ctx: Context): Promise<string> {
    try {
      const response = await this.client.post('/build', {
        request,
        user_id: ctx.from?.id,
        username: ctx.from?.username,
        task_type: 'build',
      });

      if (response.status === 200 && response.data?.result) {
        return response.data.result;
      }

      return this.formatErrorResponse(response, 'Build failed');
    } catch (error: any) {
      return `❌ Build Error: ${error.message}`;
    }
  }

  /**
   * Execute code generation
   */
  async executeCode(request: string, ctx: Context): Promise<string> {
    try {
      const response = await this.client.post('/build', {
        request,
        user_id: ctx.from?.id,
        username: ctx.from?.username,
        task_type: 'code',
      });

      if (response.status === 200 && response.data?.result) {
        return response.data.result;
      }

      return this.formatErrorResponse(response, 'Code generation failed');
    } catch (error: any) {
      return `❌ Code Error: ${error.message}`;
    }
  }

  /**
   * Execute test generation
   */
  async executeTest(request: string, ctx: Context): Promise<string> {
    try {
      const response = await this.client.post('/build', {
        request,
        user_id: ctx.from?.id,
        username: ctx.from?.username,
        task_type: 'test',
      });

      if (response.status === 200 && response.data?.result) {
        return response.data.result;
      }

      return this.formatErrorResponse(response, 'Test generation failed');
    } catch (error: any) {
      return `❌ Test Error: ${error.message}`;
    }
  }

  /**
   * Analyze code
   */
  async analyzeCode(request: string, ctx: Context): Promise<string> {
    try {
      const response = await this.client.post('/analysis', {
        request,
        user_id: ctx.from?.id,
        username: ctx.from?.username,
      });

      if (response.status === 200 && response.data?.analysis) {
        return response.data.analysis;
      }

      return this.formatErrorResponse(response, 'Analysis failed');
    } catch (error: any) {
      return `❌ Analysis Error: ${error.message}`;
    }
  }

  /**
   * Get session memory
   */
  async getMemory(userId: number): Promise<any> {
    try {
      const response = await this.client.get(`/memory/${userId}`);

      if (response.status === 200) {
        return response.data;
      }

      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Save to memory
   */
  async saveMemory(userId: number, key: string, value: any): Promise<boolean> {
    try {
      const response = await this.client.post('/memory', {
        user_id: userId,
        key,
        value,
      });

      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  /**
   * Format error response
   */
  private formatErrorResponse(response: any, defaultMsg: string): string {
    if (response.data?.error) {
      return `❌ Error: ${response.data.error}`;
    }

    if (response.data?.detail) {
      return `❌ Error: ${response.data.detail}`;
    }

    return `❌ ${defaultMsg}`;
  }

  /**
   * Get current status
   */
  getStatus(): {
    online: boolean;
    lastCheck: number;
    baseUrl: string;
  } {
    return {
      online: this.isOnline,
      lastCheck: this.lastHealthCheck,
      baseUrl: AGENT_API_BASE,
    };
  }
}

// Singleton instance
let agentAPI: AgentAPI | null = null;

export function getAgentAPI(): AgentAPI {
  if (!agentAPI) {
    agentAPI = new AgentAPI();
  }
  return agentAPI;
}

export async function initializeAgentAPI(): Promise<AgentAPI> {
  const api = getAgentAPI();
  const isHealthy = await api.checkHealth();

  if (!isHealthy) {
    console.error(
      '❌ Python Agent is not responding on ' + AGENT_API_BASE
    );
    console.error('Make sure the Python agent is running: ./start-agent.sh');
  } else {
    console.log('✅ Python Agent API is online at ' + AGENT_API_BASE);
  }

  return api;
}
