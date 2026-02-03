import { TwitterApi } from 'twitter-api-v2';
import * as schedule from 'node-schedule';
import { OllamaQwenTool } from '../tools/ollamaQwenTool';

export interface SocialMediaConfig {
  twitter?: {
    appKey: string;
    appSecret: string;
    accessToken: string;
    accessSecret: string;
    bearerToken: string;
  };
  linkedin?: {
    accessToken: string;
  };
}

export interface PostSchedule {
  id: string;
  platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube';
  content: string;
  scheduledTime: Date;
  status: 'pending' | 'posted' | 'failed';
  mediaUrls?: string[];
}

export interface ViralityResult {
  score: number;
  suggestions: string[];
  engagementPrediction: 'low' | 'medium' | 'high';
}

export class SocialMediaManager {
  private config: SocialMediaConfig;
  private twitterClient: TwitterApi | null = null;
  private scheduledPosts: Map<string, PostSchedule>;
  private jobs: Map<string, schedule.Job>;

  constructor(config?: SocialMediaConfig) {
    this.config = config || {};
    this.scheduledPosts = new Map();
    this.jobs = new Map();
    this.initializeClients();
  }

  private initializeClients(): void {
    if (this.config.twitter && this.config.twitter.bearerToken) {
      this.twitterClient = new TwitterApi(this.config.twitter.bearerToken);
    }
  }

  async postToTwitter(text: string, mediaUrls?: string[]): Promise<{ success: boolean; tweetId?: string; error?: string }> {
    if (!this.twitterClient) {
      return { success: false, error: 'Twitter client not configured' };
    }

    try {
      const result = await this.twitterClient.v2.tweet(text);

      return {
        success: true,
        tweetId: result.data.id
      };
    } catch (error) {
      console.error('Twitter post error:', error);
      return { 
        success: false, 
        error: (error as Error).message 
      };
    }
  }

  async optimizeForVirality(content: string, platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube' = 'x'): Promise<ViralityResult> {
    const qwenTool = new OllamaQwenTool();

    const prompt = `You are a social media virality expert. Analyze this post and provide:

## Post Content
${content}

## Platform
${platform}

## Your Task
1. Score the potential virality (0-100)
2. Provide 3-5 specific improvement suggestions
3. Predict engagement level (low/medium/high)
4. Keep suggestions under 50 words total

Respond in JSON format:
{
  "score": number,
  "suggestions": ["suggestion1", "suggestion2", ...],
  "engagementPrediction": "low" | "medium" | "high"
}`;

    try {
      const response = await qwenTool.chatWithOllama(prompt);
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        return parsed as ViralityResult;
      }
      
      return {
        score: 50,
        suggestions: ['Could not analyze', 'Check formatting'],
        engagementPrediction: 'medium'
      };
    } catch (error) {
      console.error('Virality analysis error:', error);
      return {
        score: 50,
        suggestions: ['Analysis failed'],
        engagementPrediction: 'medium'
      };
    }
  }

  async generateHashtags(content: string, platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube' = 'x'): Promise<string[]> {
    const { OllamaQwenTool } = await import('../tools/ollamaQwenTool.js');
    const qwenTool = new OllamaQwenTool();

    const prompt = `Generate relevant hashtags for this post. Max 10 hashtags. Platform: ${platform}

Post: ${content}

Return only hashtags separated by spaces, no explanation. Example: #coding #javascript #webdev`;

    try {
      const response = await qwenTool.chatWithOllama(prompt);
      const hashtags = response
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.startsWith('#'))
        .slice(0, 10);
      
      return hashtags;
    } catch (error) {
      console.error('Hashtag generation error:', error);
      return [];
    }
  }

  schedulePost(platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube', content: string, scheduledTime: Date, mediaUrls?: string[]): string {
    const postId = `post-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    
    const postSchedule: PostSchedule = {
      id: postId,
      platform,
      content,
      scheduledTime,
      status: 'pending',
      mediaUrls
    };
    
    this.scheduledPosts.set(postId, postSchedule);
    
    const delay = scheduledTime.getTime() - Date.now();
    
    if (delay > 0) {
      const job = schedule.scheduleJob(
        scheduledTime,
        () => this.executeScheduledPost(postId)
      );
      
      this.jobs.set(postId, job);
      console.log(`📅 Post scheduled for ${scheduledTime.toISOString()}`);
    } else {
      this.executeScheduledPost(postId);
    }
    
    return postId;
  }

  private async executeScheduledPost(postId: string): Promise<void> {
    const postSchedule = this.scheduledPosts.get(postId);
    
    if (!postSchedule) {
      return;
    }

    let result;
    
    switch (postSchedule.platform) {
      case 'x':
        result = await this.postToTwitter(postSchedule.content, postSchedule.mediaUrls);
        break;
      case 'facebook':
      case 'instagram':
      case 'linkedin':
      case 'tiktok':
      case 'youtube':
        result = { success: false, error: 'Browser automation required - use /post command' };
        break;
    }

    postSchedule.status = result.success ? 'posted' : 'failed';
    this.scheduledPosts.set(postId, postSchedule);
    
    if (this.jobs.has(postId)) {
      const job = this.jobs.get(postId);
      if (job) {
        schedule.cancelJob(job);
      }
      this.jobs.delete(postId);
    }

    console.log(`📤 Post ${result.success ? 'published' : 'failed'}: ${postId}`);
  }

  async generateViralPost(topic: string, platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube' = 'x'): Promise<{ content: string; viralityScore: number }> {
    const { OllamaQwenTool } = await import('../tools/ollamaQwenTool.js');
    const qwenTool = new OllamaQwenTool();

    const prompt = `Generate a viral social media post about: ${topic}

## Platform: ${platform}
## Requirements:
- Maximum 280 characters (Twitter) or 700 characters (LinkedIn)
- Include 2-3 relevant hashtags
- Use engaging tone
- Include emoji sparingly (2-3 max)
- Make it memorable and shareable

## Format:
Return ONLY the post content, no explanation or additional text.`;

    try {
      const content = await qwenTool.chatWithOllama(prompt);
      const virality = await this.optimizeForVirality(content, platform);
      
      return {
        content,
        viralityScore: virality.score
      };
    } catch (error) {
      console.error('Viral post generation error:', error);
      return {
        content: topic,
        viralityScore: 50
      };
    }
  }

  getScheduledPosts(): PostSchedule[] {
    return Array.from(this.scheduledPosts.values());
  }

  getPostStatus(postId: string): PostSchedule | null {
    return this.scheduledPosts.get(postId) || null;
  }

  cancelScheduledPost(postId: string): boolean {
    const postSchedule = this.scheduledPosts.get(postId);
    
    if (!postSchedule || postSchedule.status !== 'pending') {
      return false;
    }

    const job = this.jobs.get(postId);
    if (job) {
      schedule.cancelJob(job);
      this.jobs.delete(postId);
    }

    this.scheduledPosts.delete(postId);
    console.log(`🗑 Scheduled post cancelled: ${postId}`);
    return true;
  }

  getStats(): {
    totalScheduled: number;
    pending: number;
    posted: number;
    failed: number;
    byPlatform: Record<string, number>;
  } {
    const stats = {
      totalScheduled: this.scheduledPosts.size,
      pending: 0,
      posted: 0,
      failed: 0,
      byPlatform: {} as Record<string, number>
    };

    const posts = Array.from(this.scheduledPosts.values());
    for (const post of posts) {
      switch (post.status) {
        case 'pending':
          stats.pending++;
          break;
        case 'posted':
          stats.posted++;
          break;
        case 'failed':
          stats.failed++;
          break;
      }
      
      stats.byPlatform[post.platform] = (stats.byPlatform[post.platform] || 0) + 1;
    }

    return stats;
  }
}