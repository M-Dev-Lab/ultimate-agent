import { Page } from 'playwright';
import { ChromiumManager } from './chromium_manager.js';
import { getPlatformConfig } from './browser_config.js';

export interface InstagramPostOptions {
  imagePaths: string[];
  videoPaths?: string[];
  caption: string;
}

export interface InstagramPostResult {
  success: boolean;
  postId?: string;
  url?: string;
  error?: string;
}

export class InstagramHandler {
  private browser: ChromiumManager;
  private config: ReturnType<typeof getPlatformConfig>;

  constructor(browser: ChromiumManager) {
    this.browser = browser;
    this.config = getPlatformConfig('instagram');
  }

  async login(username: string, password: string): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/accounts/login/`);
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
      if (content.includes('Two-factor') || content.includes('verification')) {
        console.log('Instagram login requires two-factor authentication');
      }
      
      return true;
    } catch (error) {
      console.error('Instagram login failed:', error);
      return false;
    }
  }

  async createPost(options: InstagramPostOptions): Promise<InstagramPostResult> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(this.config.url);
      await this.browser.waitForTimeout(2000);

      const postButton = this.config.selectors.postButton;
      if (postButton) {
        await this.browser.click(postButton);
      }
      await this.browser.waitForTimeout(2000);

      const fileInput = await page.$('input[type="file"]');
      if (!fileInput) {
        return { success: false, error: 'File input not found' };
      }

      const allMedia = [
        ...options.imagePaths.map(p => ({ path: p, type: 'image' as const })),
        ...(options.videoPaths || []).map(p => ({ path: p, type: 'video' as const })),
      ];

      for (const media of allMedia) {
        await fileInput.setInputFiles(media.path);
        await this.browser.waitForTimeout(2000);
      }

      const nextButton = this.config.selectors.nextButton;
      if (nextButton) {
        await this.browser.click(nextButton);
        await this.browser.waitForTimeout(2000);
        const nextButton2 = this.config.selectors.nextButton;
        if (nextButton2) {
          await this.browser.click(nextButton2);
        }
        await this.browser.waitForTimeout(2000);
      }

      const captionBoxSelector = this.config.selectors.captionBox;
      if (captionBoxSelector) {
        const captionBox = await page.$(captionBoxSelector);
        if (captionBox) {
          await captionBox.fill(options.caption);
        }
      }

      const shareButton = this.config.selectors.shareButton;
      if (shareButton) {
        await this.browser.click(shareButton);
      }
      await this.browser.waitForTimeout(5000);

      const currentUrl = page.url();
      const urlMatch = currentUrl.match(/instagram\.com\/p\/([^\/]+)/);
      
      return {
        success: true,
        url: currentUrl,
        postId: urlMatch ? urlMatch[1] : undefined,
      };
    } catch (error) {
      console.error('Instagram post failed:', error);
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
           !content.includes('Log in');
  }

  async getUserProfile(username: string): Promise<any> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(`${this.config.url}/${username}/`);
      await this.browser.waitForTimeout(2000);
      
      const profileData = await page.evaluate(() => {
        const followerCount = document.querySelector('a[href*="followers"]')?.textContent;
        const followingCount = document.querySelector('a[href*="following"]')?.textContent;
        const postCount = document.querySelector('span[id*="post"]')?.textContent;
        
        return {
          followerCount,
          followingCount,
          postCount,
        };
      });
      
      return profileData;
    } catch (error) {
      console.error('Failed to get profile:', error);
      return null;
    }
  }
}

export default InstagramHandler;
