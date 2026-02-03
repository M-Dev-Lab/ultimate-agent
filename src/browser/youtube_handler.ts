import { Page } from 'playwright';
import { ChromiumManager } from './chromium_manager.js';
import { getPlatformConfig } from './browser_config.js';

export interface YouTubePostOptions {
  videoPath: string;
  title: string;
  description: string;
  thumbnailPath?: string;
  tags?: string[];
  playlist?: string;
  visibility: 'public' | 'unlisted' | 'private';
  publishAt?: Date;
}

export interface YouTubePostResult {
  success: boolean;
  videoId?: string;
  url?: string;
  error?: string;
}

export class YouTubeHandler {
  private browser: ChromiumManager;
  private config: ReturnType<typeof getPlatformConfig>;

  constructor(browser: ChromiumManager) {
    this.browser = browser;
    this.config = getPlatformConfig('youtube');
  }

  async login(email: string, password: string, recoveryEmail?: string): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/signin`);
      await this.browser.waitForTimeout(3000);

      const loginEmail = this.config.selectors.loginEmail;
      if (loginEmail) {
        await this.browser.fill(loginEmail, email);
      }
      await this.browser.waitForTimeout(1000);

      const nextButton = await page.$('button:has-text("Next")');
      if (nextButton) {
        await nextButton.click();
        await this.browser.waitForTimeout(2000);
      }

      const loginPassword = this.config.selectors.loginPassword;
      const loginButton = this.config.selectors.loginButton;
      
      if (loginPassword) {
        await this.browser.fill(loginPassword, password);
      }
      
      if (loginButton) {
        await this.browser.click(loginButton);
      }
      
      await this.browser.waitForTimeout(5000);

      if (recoveryEmail) {
        await this.browser.fill('input[type="email"]', recoveryEmail);
        await this.browser.click('button:has-text("Done")');
        await this.browser.waitForTimeout(2000);
      }
      
      return true;
    } catch (error) {
      console.error('YouTube login failed:', error);
      return false;
    }
  }

  async createPost(options: YouTubePostOptions): Promise<YouTubePostResult> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(this.config.url);
      await this.browser.waitForTimeout(2000);

      const uploadButton = this.config.selectors.uploadButton;
      if (uploadButton) {
        await this.browser.click(uploadButton);
      }
      await this.browser.waitForTimeout(2000);

      const fileInput = await page.$('input[type="file"]');
      if (!fileInput) {
        return { success: false, error: 'File input not found for upload' };
      }

      await fileInput.setInputFiles(options.videoPath);
      await this.browser.waitForTimeout(5000);

      const titleBoxSelector = this.config.selectors.titleBox;
      if (titleBoxSelector) {
        const titleBox = await page.$(titleBoxSelector);
        if (titleBox) {
          await titleBox.fill(options.title);
        }
      }

      const descriptionBoxSelector = this.config.selectors.descriptionBox;
      if (descriptionBoxSelector) {
        const descriptionBox = await page.$(descriptionBoxSelector);
        if (descriptionBox) {
          await descriptionBox.fill(options.description);
        }
      }

      if (options.thumbnailPath) {
        const thumbnailInput = await page.$('input[type="file"][accept*="image"]');
        if (thumbnailInput) {
          await thumbnailInput.setInputFiles(options.thumbnailPath);
          await this.browser.waitForTimeout(2000);
        }
      }

      const nextButtons = await page.$$('button:has-text("Next")');
      for (const button of nextButtons) {
        await button.click();
        await this.browser.waitForTimeout(2000);
      }

      if (options.visibility === 'public') {
        const publicButtonSelector = this.config.selectors.publicButton;
        if (publicButtonSelector) {
          const publicButton = await page.$(publicButtonSelector);
          if (publicButton) {
            await publicButton.click();
            await this.browser.waitForTimeout(1000);
          }
        }
      }

      const postButtonSelector = this.config.selectors.postButton;
      if (postButtonSelector) {
        const publishButton = await page.$(postButtonSelector);
        if (publishButton) {
          await publishButton.click();
          await this.browser.waitForTimeout(5000);
        }
      }

      const currentUrl = page.url();
      const urlMatch = currentUrl.match(/youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/);
      
      return {
        success: true,
        url: currentUrl,
        videoId: urlMatch ? urlMatch[1] : undefined,
      };
    } catch (error) {
      console.error('YouTube post failed:', error);
      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  async checkLoggedIn(): Promise<boolean> {
    await this.browser.navigate(this.config.url);
    await this.browser.waitForTimeout(2000);
    
    const content = await this.browser.getPageContent();
    return !content.includes('Sign in') && 
           !content.includes('sign in') &&
           content.includes('Create');
  }

  async getChannelStats(): Promise<any> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/channel`);
      await this.browser.waitForTimeout(3000);
      
      const stats = await page.evaluate(() => {
        const subscriberCount = document.querySelector('#subscriber-count')?.textContent;
        const viewCount = document.querySelector('#view-count')?.textContent;
        const videoCount = document.querySelector('#video-count')?.textContent;
        
        return {
          subscriberCount,
          viewCount,
          videoCount,
        };
      });
      
      return stats;
    } catch (error) {
      console.error('Failed to get channel stats:', error);
      return null;
    }
  }

  async updateVideo(videoId: string, updates: Partial<YouTubePostOptions>): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/edit_video?video_id=${videoId}`);
      await this.browser.waitForTimeout(3000);

      if (updates.title) {
        const titleBoxSelector = this.config.selectors.titleBox;
        if (titleBoxSelector) {
          const titleBox = await page.$(titleBoxSelector);
          if (titleBox) {
            await titleBox.fill(updates.title);
          }
        }
      }

      if (updates.description) {
        const descriptionBoxSelector = this.config.selectors.descriptionBox;
        if (descriptionBoxSelector) {
          const descriptionBox = await page.$(descriptionBoxSelector);
          if (descriptionBox) {
            await descriptionBox.fill(updates.description);
          }
        }
      }

      const saveButton = await page.$('button:has-text("Save")');
      if (saveButton) {
        await saveButton.click();
        await this.browser.waitForTimeout(2000);
      }
      
      return true;
    } catch (error) {
      console.error('Failed to update video:', error);
      return false;
    }
  }
}

export default YouTubeHandler;
