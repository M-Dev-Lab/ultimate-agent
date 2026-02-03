import { MemoryManager } from '../memory/memory_manager.js';
import { OllamaQwenTool } from '../tools/ollamaQwenTool.js';

export interface ModelConfig {
  name: string;
  provider: string;
  contextWindow: number;
  speed: 'fast' | 'medium' | 'slow';
  costPer1kInput?: number;
  costPer1kOutput?: number;
  monthlyFreeRequests?: number;
}

export interface QuotaInfo {
  requestsUsed: number;
  requestsRemaining: number;
  resetTime: Date | null;
}

export type ModelTier = 'cloud_ollama' | 'local_small' | 'local_medium' | 'paid_api';
export type Priority = 'low' | 'normal' | 'high' | 'critical';

export class ModelRouter {
  private memory: MemoryManager;
  private client: OllamaQwenTool;
  private config: ModelConfig[];
  private quota: QuotaInfo;
  private usageStats: Map<string, { uses: number; successRate: number; avgTime: number }>;
  private cloudAvailable: boolean = false;
  private cloudApiKey: string | null = null;

  constructor(memory: MemoryManager) {
    this.memory = memory;
    this.client = new OllamaQwenTool();
    this.config = this.getDefaultConfig();
    this.quota = {
      requestsUsed: 0,
      requestsRemaining: Infinity,
      resetTime: null
    };
    this.usageStats = new Map();
    this.checkCloudAvailability();
  }

  private async checkCloudAvailability(): Promise<void> {
    this.cloudApiKey = process.env.OLLAMA_CLOUD_API_KEY || null;
    if (this.cloudApiKey) {
      try {
        const response = await fetch('https://api.ollama.com/api/tags', {
          headers: { 'Authorization': `Bearer ${this.cloudApiKey}` },
          signal: AbortSignal.timeout(3000)
        });
        if (response.ok) {
          this.cloudAvailable = true;
          console.log('☁️ Ollama Cloud detected - will use cloud for complex tasks');
        }
      } catch (e) {
        this.cloudAvailable = false;
      }
    }
  }

  private getDefaultConfig(): ModelConfig[] {
    return [
      {
        name: 'qwen3-coder:30b',
        provider: 'ollama-cloud',
        contextWindow: 131072,
        speed: 'fast',
        costPer1kInput: 0,
        costPer1kOutput: 0,
        monthlyFreeRequests: 100000
      },
      {
        name: 'llava-phi3:latest',
        provider: 'ollama',
        contextWindow: 4096,
        speed: 'fast',
        costPer1kInput: 0,
        costPer1kOutput: 0
      },
      {
        name: 'qwen2.5-coder:7b',
        provider: 'ollama',
        contextWindow: 32768,
        speed: 'medium',
        costPer1kInput: 0,
        costPer1kOutput: 0
      }
    ];
  }

  async routeRequest(command: string, userInput: string, priority: Priority = 'normal'): Promise<{ model: ModelConfig; tier: ModelTier }> {
    const complexity = this.estimateComplexity(userInput);
    
    if (this.cloudAvailable && (complexity === 'high' || priority === 'high' || priority === 'critical')) {
      const cloudConfig = this.config.find(m => m.provider === 'ollama-cloud');
      if (cloudConfig) {
        return { model: cloudConfig, tier: 'cloud_ollama' };
      }
    }

    const preferredTier = this.getPreferredTier(command, complexity, priority);

    const modelConfig = this.config.find(m => m.name === preferredTier);
    
    if (!modelConfig) {
      const defaultConfig = this.config[0];
      return {
        model: defaultConfig,
        tier: this.getTier(defaultConfig)
      };
    }

    return {
      model: modelConfig,
      tier: this.getTier(modelConfig)
    };
  }

  private estimateComplexity(text: string): 'low' | 'medium' | 'high' {
    const words = text.split(' ').length;
    const textLower = text.toLowerCase();

    const highKeywords = [
      'full', 'complete', 'entire', 'complex', 'advanced',
      'optimize', 'refactor', 'architect', 'design system',
      'e-commerce', 'authentication', 'database', 'api'
    ];

    const mediumKeywords = [
      'component', 'function', 'api endpoint', 'style',
      'fix bug', 'add feature', 'implement'
    ];

    if (highKeywords.some(kw => textLower.includes(kw)) || words > 50) {
      return 'high';
    }

    if (mediumKeywords.some(kw => textLower.includes(kw)) || words > 20) {
      return 'medium';
    }

    return 'low';
  }

  private getPreferredTier(command: string, complexity: 'low' | 'medium' | 'high', priority: Priority): string {
    if (command === '/heartbeat' || command === 'status') {
      return 'llava-phi3:latest';
    }

    if (command === '/build' || command === '/code' || command === '/fix') {
      if (complexity === 'high' || priority === 'high' || priority === 'critical') {
        if (this.cloudAvailable) {
          return 'qwen3-coder:30b';
        }
      }
      return 'qwen2.5-coder:7b';
    }

    if (command === '/learn' || command === '/analytics' || command === '/improve') {
      if (this.cloudAvailable) {
        return 'qwen3-coder:30b';
      }
      return 'qwen2.5-coder:7b';
    }

    if (command === '/post' || command === '/viral') {
      if (complexity === 'high') {
        if (this.cloudAvailable) {
          return 'qwen3-coder:30b';
        }
      }
      return 'qwen2.5-coder:7b';
    }

    if (command === '/deploy' || command === '/audit' || priority === 'critical') {
      if (this.cloudAvailable) {
        return 'qwen3-coder:30b';
      }
      return 'qwen2.5-coder:7b';
    }

    return 'qwen2.5-coder:7b';
  }

  private getTier(config: ModelConfig): ModelTier {
    if (config.provider === 'ollama-cloud') {
      return 'cloud_ollama';
    } else if (config.speed === 'fast') {
      return 'local_small';
    } else {
      return 'local_medium';
    }
  }

  private hasQuota(tier: ModelTier): boolean {
    if (tier === 'cloud_ollama') {
      return this.quota.requestsRemaining > 100;
    }
    return false;
  }

  trackUsage(command: string, modelConfig: ModelConfig, success: boolean, executionTime: number): void {
    const modelKey = modelConfig.name;
    
    if (!this.usageStats.has(modelKey)) {
      this.usageStats.set(modelKey, {
        uses: 0,
        successRate: 0,
        avgTime: 0
      });
    }

    const stats = this.usageStats.get(modelKey);
    if (stats) {
      stats.uses = (stats.uses || 0) + 1;
      
      if (success) {
        const currentRate = stats.successRate || 0.5;
        stats.successRate = currentRate * 0.9 + 0.1;
      } else {
        stats.successRate = stats.successRate || 0.5;
        stats.successRate = Math.max(0, stats.successRate - 0.1);
      }
      
      stats.avgTime = ((stats.avgTime * stats.uses) + executionTime) / (stats.uses + 1);
      
      this.usageStats.set(modelKey, stats);
    }

    if (modelConfig.provider !== 'ollama') {
      this.quota.requestsUsed++;
      this.quota.requestsRemaining = Math.max(0, this.quota.requestsRemaining - 1);
    }
  }

  getUsageStats(): Map<string, { uses: number; successRate: number; avgTime: number }> {
    return new Map(this.usageStats);
  }

  getQuotaInfo(): QuotaInfo {
    return { ...this.quota };
  }

  setQuotaLimits(limits: Partial<QuotaInfo>): void {
    this.quota = { ...this.quota, ...limits };
  }
}