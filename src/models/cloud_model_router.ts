import { CloudModelConfig, ModelProviderConfig, defaultModelConfig, ModelResponse, ContentOptimizationRequest, ContentOptimizationResponse } from './cloud_model_provider.js';

export class CloudModelRouter {
  private config: ModelProviderConfig;
  private currentCloudModel: CloudModelConfig | null = null;
  private localModelAvailable: boolean = false;
  private localModelName: string = 'llava-phi3:latest';

  constructor(config?: Partial<ModelProviderConfig>) {
    this.config = { ...defaultModelConfig, ...config };
    this.initializeModels();
  }

  private initializeModels(): void {
    const availableCloudModels = this.config.cloudModels.filter(m => m.apiKey);
    
    if (availableCloudModels.length > 0) {
      availableCloudModels.sort((a, b) => a.priority - b.priority);
      this.currentCloudModel = availableCloudModels[0];
      console.log(`☁️ Primary cloud model: ${this.currentCloudModel.name} (${this.currentCloudModel.modelSize})`);
      console.log(`📋 Available cloud models: ${availableCloudModels.map(m => m.name).join(', ')}`);
    } else {
      console.warn('⚠️ No cloud models configured, will use local fallback');
    }

    this.localModelAvailable = this.checkLocalOllama();
  }

  private checkLocalOllama(): boolean {
    const ollamaHost = process.env.OLLAMA_HOST || '127.0.0.1';
    const ollamaPort = process.env.OLLAMA_PORT || '11434';
    
    try {
      const models = process.env.OLLAMA_MODEL;
      if (models) {
        this.localModelName = models;
        return true;
      }
    } catch {
      return false;
    }
    return !!process.env.OLLAMA_MODEL;
  }

  async complete(prompt: string, options?: { temperature?: number; maxTokens?: number }): Promise<ModelResponse> {
    const startTime = Date.now();
    const maxTokens = options?.maxTokens || 4096;
    const temperature = options?.temperature || 0.7;

    if (this.currentCloudModel) {
      try {
        const result = await this.callCloudModel(this.currentCloudModel, prompt, temperature, maxTokens);
        if (result.success) {
          return {
            ...result,
            executionTime: Date.now() - startTime,
          };
        }
        console.warn(`⚠️ Cloud model ${this.currentCloudModel.name} failed: ${result.error}`);
        
        if (this.config.maxRetries > 1) {
          for (let i = 1; i < this.config.cloudModels.length; i++) {
            const fallbackModel = this.config.cloudModels[i];
            if (fallbackModel.apiKey) {
              console.log(`🔄 Trying fallback cloud model: ${fallbackModel.name}`);
              const fallbackResult = await this.callCloudModel(fallbackModel, prompt, temperature, maxTokens);
              if (fallbackResult.success) {
                return {
                  ...fallbackResult,
                  executionTime: Date.now() - startTime,
                };
              }
            }
          }
        }
      } catch (error: any) {
        console.warn(`⚠️ Cloud model error: ${error.message}`);
      }
    }

    if (this.config.localFallback && this.localModelAvailable) {
      console.log('🔄 Falling back to local Ollama model...');
      return await this.callLocalModel(prompt, temperature, maxTokens, startTime);
    }

    return {
      success: false,
      content: '',
      model: 'none',
      provider: 'local',
      error: 'All models failed',
      executionTime: Date.now() - startTime,
    };
  }

  private async callCloudModel(model: CloudModelConfig, prompt: string, temperature: number, maxTokens: number): Promise<ModelResponse> {
    try {
      const response = await fetch(`${model.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${model.apiKey}`,
        },
        body: JSON.stringify({
          model: model.name,
          messages: [{ role: 'user', content: prompt }],
          temperature,
          max_tokens: maxTokens,
          stream: false,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        return {
          success: false,
          content: '',
          model: model.name,
          provider: 'cloud',
          error: `API error: ${response.status} - ${error}`,
          executionTime: 0,
        };
      }

      const data = await response.json();
      const content = data.choices?.[0]?.message?.content || '';

      return {
        success: true,
        content,
        model: model.name,
        provider: 'cloud',
        executionTime: 0,
      };
    } catch (error: any) {
      return {
        success: false,
        content: '',
        model: model.name,
        provider: 'cloud',
        error: error.message,
        executionTime: 0,
      };
    }
  }

  private async callLocalModel(prompt: string, temperature: number, maxTokens: number, startTime: number): Promise<ModelResponse> {
    try {
      const { default: ollama } = await import('ollama');
      
      const response = await ollama.chat({
        model: this.localModelName,
        messages: [{ role: 'user', content: prompt }],
        options: {
          temperature,
          num_predict: maxTokens,
          top_p: 0.9,
          top_k: 40,
        },
        stream: false,
      });

      return {
        success: true,
        content: response.message?.content || '',
        model: this.localModelName,
        provider: 'local',
        executionTime: Date.now() - startTime,
      };
    } catch (error: any) {
      return {
        success: false,
        content: '',
        model: this.localModelName,
        provider: 'local',
        error: error.message,
        executionTime: Date.now() - startTime,
      };
    }
  }

  async optimizeContent(request: ContentOptimizationRequest): Promise<ContentOptimizationResponse> {
    const { content, platform, task } = request;

    let systemPrompt: string;
    switch (task) {
      case 'virality':
        systemPrompt = `You are a social media virality expert. Analyze this post and provide improvements. Return JSON with: score (0-100), suggestions (array), engagementPrediction (low/medium/high).`;
        break;
      case 'hashtags':
        systemPrompt = `Generate relevant hashtags for this post. Max 10. Return ONLY hashtags separated by spaces.`;
        break;
      case 'viral_post':
        systemPrompt = `Generate viral content for ${platform}. Maximum ${platform === 'instagram' ? '2200' : '280'} characters. Include 2-3 hashtags. Engaging tone. Return ONLY the content.`;
        break;
      default:
        systemPrompt = `Optimize this content for ${platform}. Return the improved version.`;
    }

    const prompt = `${systemPrompt}\n\nContent: ${content}`;
    const result = await this.complete(prompt, { temperature: 0.7, maxTokens: 2000 });

    if (!result.success) {
      return { optimizedContent: content };
    }

    const resultContent = result.content || '';
    const response: ContentOptimizationResponse = { optimizedContent: resultContent };

    try {
      if (task === 'virality') {
        const parsed = JSON.parse(resultContent);
        response.score = parsed.score;
        response.suggestions = parsed.suggestions;
      } else if (task === 'hashtags') {
        response.hashtags = resultContent.split(' ').filter((h: string) => h.startsWith('#'));
      } else {
        response.optimizedContent = resultContent;
      }
    } catch {
      response.optimizedContent = resultContent;
    }

    return response;
  }

  async generateViralPost(topic: string, platform: string): Promise<{ content: string; viralityScore: number }> {
    let prompt: string;

    if (platform === 'youtube') {
      prompt = `Generate YouTube content about: ${topic}\n\nReturn JSON: { "title": "...", "description": "...", "tags": [...] }`;
    } else if (platform === 'instagram') {
      prompt = `Generate Instagram caption about: ${topic}\n\nMax 2200 chars, 2-3 hashtags. Return ONLY the caption.`;
    } else {
      prompt = `Generate viral post about: ${topic}\n\nMax 280 chars, 2-3 hashtags. Return ONLY the content.`;
    }

    const result = await this.complete(prompt, { temperature: 0.8, maxTokens: 1000 });

    if (!result.success) {
      return { content: topic, viralityScore: 50 };
    }

    let content = result.content || topic;
    let viralityScore = 70;

    try {
      if (platform === 'youtube') {
        const parsed = JSON.parse(result.content || '{}');
        content = JSON.stringify(parsed);
      }
    } catch {
      viralityScore = 60;
    }

    return { content, viralityScore };
  }

  getCurrentModel(): { name: string; provider: 'cloud' | 'local'; size?: string } {
    if (this.currentCloudModel) {
      return {
        name: this.currentCloudModel.name,
        provider: 'cloud',
        size: this.currentCloudModel.modelSize,
      };
    }
    return {
      name: this.localModelName,
      provider: 'local',
    };
  }

  isCloudAvailable(): boolean {
    return this.currentCloudModel !== null;
  }

  isLocalAvailable(): boolean {
    return this.localModelAvailable;
  }

  async healthCheck(): Promise<{ cloud: boolean; local: boolean; current: string }> {
    return {
      cloud: this.isCloudAvailable(),
      local: this.isLocalAvailable(),
      current: this.getCurrentModel().name,
    };
  }
}

export default CloudModelRouter;
