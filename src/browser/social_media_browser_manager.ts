import { TwitterApi } from 'twitter-api-v2';
import * as schedule from 'node-schedule';
import { OllamaQwenTool } from '../tools/ollamaQwenTool.js';
import { ChromiumManager } from './chromium_manager.js';
import { FacebookHandler, FacebookPostOptions } from './facebook_handler.js';
import { InstagramHandler, InstagramPostOptions } from './instagram_handler.js';
import { TikTokHandler, TikTokPostOptions } from './tiktok_handler.js';
import { YouTubeHandler, YouTubePostOptions } from './youtube_handler.js';
import { XHandler, XPostOptions } from './x_handler.js';
import { LinkedInHandler, LinkedInPostOptions } from './linkedin_handler.js';
import { BrowserConfig, PlatformCredentials } from './browser_config.js';
import { CloudModelRouter } from '../models/cloud_model_router.js';

export interface SocialMediaConfig {
  twitter?: {
    appKey: string;
    appSecret: string;
    accessToken: string;
    accessSecret: string;
    bearerToken: string;
  };
  browser?: BrowserConfig;
  credentials?: PlatformCredentials;
  useCloudModels?: boolean;
}

export interface BrowserPostSchedule {
  id: string;
  platform: 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube';
  content: any;
  scheduledTime: Date;
  status: 'pending' | 'posted' | 'failed';
  mediaPaths?: string[];
}

export interface ViralityResult {
  score: number;
  suggestions: string[];
  engagementPrediction: 'low' | 'medium' | 'high';
}

export type SupportedPlatform = 'facebook' | 'instagram' | 'x' | 'linkedin' | 'tiktok' | 'youtube';

export class SocialMediaBrowserManager {
  private config: SocialMediaConfig;
  private twitterClient: TwitterApi | null = null;
  private scheduledPosts: Map<string, BrowserPostSchedule>;
  private jobs: Map<string, schedule.Job>;
  private chromiumManager: ChromiumManager | null = null;
  private facebookHandler: FacebookHandler | null = null;
  private instagramHandler: InstagramHandler | null = null;
  private tiktokHandler: TikTokHandler | null = null;
  private youTubeHandler: YouTubeHandler | null = null;
  private xHandler: XHandler | null = null;
  private linkedInHandler: LinkedInHandler | null = null;
  private browserInitialized: boolean = false;
  private modelRouter: CloudModelRouter;

  constructor(config?: SocialMediaConfig) {
    this.config = config || {};
    this.scheduledPosts = new Map();
    this.jobs = new Map();
    this.modelRouter = new CloudModelRouter();
    this.initializeClients();
  }

  private initializeClients(): void {
    if (this.config.twitter && this.config.twitter.bearerToken) {
      this.twitterClient = new TwitterApi(this.config.twitter.bearerToken);
    }
    this.logModelStatus();
  }

  private logModelStatus(): void {
    const status = this.modelRouter.healthCheck();
    status.then(s => {
      console.log(`🤖 Model Status - Cloud: ${s.cloud}, Local: ${s.local}, Current: ${s.current}`);
    });
  }

  async initializeBrowser(): Promise<void> {
    if (this.browserInitialized) {
      return;
    }

    try {
      this.chromiumManager = new ChromiumManager(this.config.browser);
      await this.chromiumManager.launch();
      
      this.facebookHandler = new FacebookHandler(this.chromiumManager);
      this.instagramHandler = new InstagramHandler(this.chromiumManager);
      this.tiktokHandler = new TikTokHandler(this.chromiumManager);
      this.youTubeHandler = new YouTubeHandler(this.chromiumManager);
      this.xHandler = new XHandler(this.chromiumManager);
      this.linkedInHandler = new LinkedInHandler(this.chromiumManager);
      
      this.browserInitialized = true;
      console.log('Browser automation initialized successfully');
    } catch (error) {
      console.error('Failed to initialize browser:', error);
      throw error;
    }
  }

  async postToX(text: string, mediaUrls?: string[]): Promise<{ success: boolean; postId?: string; error?: string }> {
    return { success: false, error: 'X API posting not supported - use browser posting' };
  }

  async postToXBrowser(options: XPostOptions): Promise<{ success: boolean; postId?: string; url?: string; error?: string }> {
    try {
      await this.initializeBrowser();
      
      if (!this.xHandler) {
        return { success: false, error: 'X handler not initialized' };
      }

      const isLoggedIn = await this.xHandler.checkLoggedIn();
      if (!isLoggedIn) {
        console.log('[Browser] Not logged in to X - please log in manually in the browser window');
        // Attempt to navigate to login page
        await this.navigateToPlatform('x');
      }

      return await this.xHandler.createPost(options);
    } catch (error: any) {
      console.error('[X Browser] Posting failed:', error);
      return { 
        success: false, 
        error: `Failed to post to X: ${error.message || 'Unknown error'}. Please check browser window.` 
      };
    }
  }
  
  async navigateToPlatform(platform: string): Promise<boolean> {
    if (!this.chromiumManager) {
      console.error('Browser not initialized');
      return false;
    }
    
    try {
      const page = await this.chromiumManager.getNewPage();
      let url: string;
      
      switch (platform.toLowerCase()) {
        case 'x':
        case 'twitter':
          url = 'https://x.com/login';
          break;
        case 'facebook':
          url = 'https://facebook.com/login';
          break;
        case 'instagram':
          url = 'https://instagram.com/accounts/login';
          break;
        case 'linkedin':
          url = 'https://linkedin.com/login';
          break;
        case 'tiktok':
          url = 'https://tiktok.com/login';
          break;
        case 'youtube':
          url = 'https://accounts.google.com/signin/v2/identifier?service=youtube';
          break;
        default:
          console.error(`Unknown platform: ${platform}`);
          return false;
      }
      
      await page.goto(url, { waitUntil: 'networkidle' });
      console.log(`[Navigation] Navigated to ${platform} login page`);
      return true;
    } catch (error) {
      console.error(`[Navigation] Failed to navigate to ${platform}:`, error);
      return false;
    }
  }

  async postToFacebook(options: FacebookPostOptions): Promise<{ success: boolean; postId?: string; url?: string; error?: string }> {
    await this.initializeBrowser();
    
    if (!this.facebookHandler) {
      return { success: false, error: 'Facebook handler not initialized' };
    }

    return await this.facebookHandler.createPost(options);
  }

  async postToInstagram(options: InstagramPostOptions): Promise<{ success: boolean; postId?: string; url?: string; error?: string }> {
    await this.initializeBrowser();
    
    if (!this.instagramHandler) {
      return { success: false, error: 'Instagram handler not initialized' };
    }

    return await this.instagramHandler.createPost(options);
  }

  async postToTikTok(options: TikTokPostOptions): Promise<{ success: boolean; postId?: string; url?: string; error?: string }> {
    await this.initializeBrowser();
    
    if (!this.tiktokHandler) {
      return { success: false, error: 'TikTok handler not initialized' };
    }

    return await this.tiktokHandler.createPost(options);
  }

  async postToYouTube(options: YouTubePostOptions): Promise<{ success: boolean; videoId?: string; url?: string; error?: string }> {
    await this.initializeBrowser();
    
    if (!this.youTubeHandler) {
      return { success: false, error: 'YouTube handler not initialized' };
    }

    const isLoggedIn = await this.youTubeHandler.checkLoggedIn();
    if (!isLoggedIn) {
      console.log('[Browser] Not logged in to YouTube - please log in manually in the browser window');
    }

    return await this.youTubeHandler.createPost(options);
  }

  async postToLinkedIn(options: LinkedInPostOptions): Promise<{ success: boolean; postId?: string; url?: string; error?: string }> {
    await this.initializeBrowser();
    
    if (!this.linkedInHandler) {
      return { success: false, error: 'LinkedIn handler not initialized' };
    }

    const isLoggedIn = await this.linkedInHandler.checkLoggedIn();
    if (!isLoggedIn) {
      console.log('[Browser] Not logged in to LinkedIn - please log in manually in the browser window');
    }

    return await this.linkedInHandler.createPost(options);
  }

  async postToPlatform(platform: SupportedPlatform, content: any): Promise<any> {
    switch (platform) {
      case 'x':
        if (typeof content === 'string') {
          return await this.postToXBrowser({ content });
        }
        return { success: false, error: 'Invalid content for X' };
      
      case 'facebook':
        return await this.postToFacebook(content as FacebookPostOptions);
      
      case 'instagram':
        return await this.postToInstagram(content as InstagramPostOptions);
      
      case 'tiktok':
        return await this.postToTikTok(content as TikTokPostOptions);
      
      case 'youtube':
        return await this.postToYouTube(content as YouTubePostOptions);
      
      case 'linkedin':
        return await this.postToLinkedIn(content);
      
      default:
        return { success: false, error: `Unknown platform: ${platform}` };
    }
  }

  async optimizeForVirality(content: string, platform: SupportedPlatform = 'x'): Promise<ViralityResult> {
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
      const result = await this.modelRouter.complete(prompt, { temperature: 0.3, maxTokens: 1000 });
      
      if (result.success && result.content) {
        const jsonMatch = result.content.match(/\{[\s\S]*\}/);
        
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          return parsed as ViralityResult;
        }
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

  async generateHashtags(content: string, platform: SupportedPlatform = 'x'): Promise<string[]> {
    const prompt = `Generate relevant hashtags for this post. Max 10 hashtags. Platform: ${platform}

Post: ${content}

Return only hashtags separated by spaces, no explanation. Example: #coding #javascript #webdev`;

    try {
      const result = await this.modelRouter.complete(prompt, { temperature: 0.3, maxTokens: 500 });
      const response = result.content || '';
      
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

  scheduleBrowserPost(
    platform: 'facebook' | 'instagram' | 'tiktok' | 'youtube',
    content: any,
    scheduledTime: Date,
    mediaPaths?: string[]
  ): string {
    const postId = `browser-post-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    
    const postSchedule: BrowserPostSchedule = {
      id: postId,
      platform,
      content,
      scheduledTime,
      status: 'pending',
      mediaPaths
    };
    
    this.scheduledPosts.set(postId, postSchedule);
    
    const delay = scheduledTime.getTime() - Date.now();
    
    if (delay > 0) {
      const job = schedule.scheduleJob(
        scheduledTime,
        () => this.executeBrowserScheduledPost(postId)
      );
      
      this.jobs.set(postId, job);
      console.log(`📅 Browser post scheduled for ${scheduledTime.toISOString()} on ${platform}`);
    } else {
      this.executeBrowserScheduledPost(postId);
    }
    
    return postId;
  }

  private async executeBrowserScheduledPost(postId: string): Promise<void> {
    const postSchedule = this.scheduledPosts.get(postId);
    
    if (!postSchedule) {
      return;
    }

    let result;
    
    switch (postSchedule.platform) {
      case 'facebook':
        result = await this.postToFacebook(postSchedule.content as FacebookPostOptions);
        break;
      case 'instagram':
        result = await this.postToInstagram(postSchedule.content as InstagramPostOptions);
        break;
      case 'tiktok':
        result = await this.postToTikTok(postSchedule.content as TikTokPostOptions);
        break;
      case 'youtube':
        result = await this.postToYouTube(postSchedule.content as YouTubePostOptions);
        break;
      default:
        result = { success: false, error: 'Unknown platform' };
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

    console.log(`📤 Browser post ${result.success ? 'published' : 'failed'} on ${postSchedule.platform}: ${postId}`);
  }

  async generateViralPost(topic: string, platform: SupportedPlatform = 'x'): Promise<{ content: any; viralityScore: number }> {
    let prompt: string;
    
    if (platform === 'youtube') {
      prompt = `Generate a YouTube video upload about: ${topic}

## Requirements:
- Title: Maximum 100 characters
- Description: Maximum 5000 characters
- Include relevant tags (5-10)
- Engaging tone
- Include call-to-action

## Format:
Return ONLY a JSON object:
{
  "title": "video title",
  "description": "video description",
  "tags": ["tag1", "tag2", ...]
}`;
    } else if (platform === 'instagram') {
      prompt = `Generate an Instagram post about: ${topic}

## Requirements:
- Caption: Maximum 2200 characters
- Include 2-3 relevant hashtags
- Engaging tone
- Include emoji sparingly (2-3 max)

## Format:
Return ONLY the caption content, no explanation.`;
    } else {
      prompt = `Generate a viral social media post about: ${topic}

## Platform: ${platform}
## Requirements:
- Maximum 280 characters
- Include 2-3 relevant hashtags
- Use engaging tone
- Include emoji sparingly (2-3 max)
- Make it memorable and shareable

## Format:
Return ONLY the post content, no explanation or additional text.`;
    }

    try {
      const result = await this.modelRouter.complete(prompt, { temperature: 0.8, maxTokens: 2000 });
      const response = result.content || '';
      
      let content: any;
      
      if (platform === 'youtube') {
        try {
          const jsonMatch = response.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            content = JSON.parse(jsonMatch[0]);
          }
        } catch {
          content = { title: topic, description: '', tags: [] };
        }
      } else {
        content = response;
      }
      
      const virality = await this.optimizeForVirality(
        typeof content === 'string' ? content : JSON.stringify(content),
        platform
      );
      
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

  getScheduledPosts(): BrowserPostSchedule[] {
    return Array.from(this.scheduledPosts.values());
  }

  getPostStatus(postId: string): BrowserPostSchedule | null {
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
    console.log(`🗑 Scheduled browser post cancelled: ${postId}`);
    return true;
  }

  async closeBrowser(): Promise<void> {
    if (this.chromiumManager) {
      await this.chromiumManager.close();
      this.chromiumManager = null;
      this.browserInitialized = false;
      console.log('Browser automation closed');
    }
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

  async switchBrowser(browserType: 'chromium' | 'firefox' | 'webkit'): Promise<void> {
    if (this.chromiumManager) {
      await this.closeBrowser();
    }
    
    this.chromiumManager = new ChromiumManager(this.config.browser, browserType);
    await this.chromiumManager.launch();
    
    this.facebookHandler = new FacebookHandler(this.chromiumManager);
    this.instagramHandler = new InstagramHandler(this.chromiumManager);
    this.tiktokHandler = new TikTokHandler(this.chromiumManager);
    this.youTubeHandler = new YouTubeHandler(this.chromiumManager);
    this.xHandler = new XHandler(this.chromiumManager);
    this.linkedInHandler = new LinkedInHandler(this.chromiumManager);
    
    this.browserInitialized = true;
    console.log(`Switched to ${browserType} browser`);
  }

  getCurrentBrowserType(): 'chromium' | 'firefox' | 'webkit' | null {
    return this.chromiumManager?.getBrowserType() || null;
  }

  isBrowserActive(): boolean {
    return this.chromiumManager?.isActive() || false;
  }

  async getModelStatus(): Promise<{ cloud: boolean; local: boolean; current: string; model: string }> {
    const health = await this.modelRouter.healthCheck();
    const currentModel = this.modelRouter.getCurrentModel();
    return {
      cloud: health.cloud,
      local: health.local,
      current: health.current,
      model: currentModel.name,
    };
  }
}

export default SocialMediaBrowserManager;
