export interface CloudModelConfig {
  name: string;
  provider: 'qwen-cloud' | 'deepseek-cloud' | 'gpt-oss' | 'ollama';
  apiKey?: string;
  baseUrl?: string;
  modelSize: string;
  priority: number;
}

export interface ModelProviderConfig {
  cloudModels: CloudModelConfig[];
  localFallback: boolean;
  timeout: number;
  maxRetries: number;
}

export const defaultModelConfig: ModelProviderConfig = {
  cloudModels: [
    {
      name: 'qwen3-coder-480b',
      provider: 'qwen-cloud',
      apiKey: process.env.QWEN_API_KEY || '',
      baseUrl: process.env.QWEN_BASE_URL || 'https://api.qwen.com/v1',
      modelSize: '480B',
      priority: 1,
    },
    {
      name: 'deepseek-v3.1',
      provider: 'deepseek-cloud',
      apiKey: process.env.DEEPSEEK_API_KEY || '',
      baseUrl: process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com/v1',
      modelSize: '671B',
      priority: 2,
    },
    {
      name: 'gpt-oss-120b',
      provider: 'gpt-oss',
      apiKey: process.env.GPTOSS_API_KEY || '',
      baseUrl: process.env.GPTOSS_BASE_URL || 'https://api.gpt-oss.example.com/v1',
      modelSize: '120B',
      priority: 3,
    },
  ],
  localFallback: true,
  timeout: 30000,
  maxRetries: 2,
};

export type ModelProvider = 'cloud' | 'local';

export interface ModelResponse {
  success: boolean;
  content?: string;
  model: string;
  provider: ModelProvider;
  error?: string;
  executionTime: number;
}

export interface ContentOptimizationRequest {
  content: string;
  platform: string;
  task: 'virality' | 'hashtags' | 'viral_post' | 'general';
}

export interface ContentOptimizationResponse {
  optimizedContent: string;
  score?: number;
  suggestions?: string[];
  hashtags?: string[];
}
