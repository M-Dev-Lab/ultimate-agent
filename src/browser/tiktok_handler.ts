import { Page } from 'playwright';
import { ChromiumManager } from './chromium_manager.js';
import { getPlatformConfig } from './browser_config.js';

export interface TikTokPostOptions {
  videoPath: string;
  caption: string;
  disableComments?: boolean;
  duetDisabled?: boolean;
  stitchDisabled?: boolean;
}

export interface TikTokPostResult {
  success: boolean;
  postId?: string;
  url?: string;
  error?: string;
}

export class TikTokHandler {
  private browser: ChromiumManager;
  private config: ReturnType<typeof getPlatformConfig>;

  constructor(browser: ChromiumManager) {
    this.browser = browser;
    this.config = getPlatformConfig('tiktok');
  }

  async login(username: string, password: string): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/login`);
      await this.browser.waitForTimeout(3000);

      const loginUsername = this.config.selectors.loginUsername;
      const loginPassword = this.config.selectors.loginPassword;
      const loginButton = this.config.selectors.loginButton;
      
      if (loginUsername && loginPassword) {
        await this.browser.fill(loginUsername, username);
        await this.browser.fill(loginPassword, password);
      }
      
      if (loginButton) {
        await this.browser.click(loginButton);
      }
      
      await this.browser.waitForTimeout(5000);

      const content = await this.browser.getPageContent();
      if (content.includes('verification') || content.includes('code')) {
        console.log('TikTok login may require additional verification');
      }
      
      return true;
    } catch (error) {
      console.error('TikTok login failed:', error);
      return false;
    }
  }

  async createPost(options: TikTokPostOptions): Promise<TikTokPostResult> {
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
      await this.browser.waitForTimeout(3000);

      const captionBox = await page.$('[contenteditable="true"], #video-description');
      if (captionBox) {
        await captionBox.fill(options.caption);
      }

      await this.browser.waitForTimeout(2000);

      const nextButtonSelector = this.config.selectors.nextButton;
      if (nextButtonSelector) {
        const nextButton = await page.$(nextButtonSelector);
        if (nextButton) {
          await nextButton.click();
          await this.browser.waitForTimeout(2000);
        }
      }

      const postButtonSelector = this.config.selectors.postButton;
      if (postButtonSelector) {
        const postButton = await page.$(postButtonSelector);
        if (postButton) {
          await postButton.click();
          await this.browser.waitForTimeout(5000);
        }
      }

      const currentUrl = page.url();
      const urlMatch = currentUrl.match(/tiktok\.com\/(@[^\/]+)\/video\/(\d+)/);
      
      return {
        success: true,
        url: currentUrl,
        postId: urlMatch ? urlMatch[2] : undefined,
      };
    } catch (error) {
      console.error('TikTok post failed:', error);
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
    return !content.includes('login') && 
           !content.includes('Log in') &&
           !content.includes('sign in');
  }

  async getVideoStats(videoUrl: string): Promise<any> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(videoUrl);
      await this.browser.waitForTimeout(3000);
      
      const stats = await page.evaluate(() => {
        const likeCount = document.querySelector('[data-e2e*="like"]')?.textContent;
        const commentCount = document.querySelector('[data-e2e*="comment"]')?.textContent;
        const shareCount = document.querySelector('[data-e2e*="share"]')?.textContent;
        
        return {
          likeCount,
          commentCount,
          shareCount,
        };
      });
      
      return stats;
    } catch (error) {
      console.error('Failed to get video stats:', error);
      return null;
    }
  }
}

export default TikTokHandler;
