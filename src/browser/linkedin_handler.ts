import { ChromiumManager } from './chromium_manager.js';
import { getPlatformConfig } from './browser_config.js';

export interface LinkedInPostOptions {
  content: string;
  mediaPaths?: string[];
  visibility: 'public' | 'connections' | 'private';
}

export interface LinkedInPostResult {
  success: boolean;
  postId?: string;
  url?: string;
  error?: string;
}

export class LinkedInHandler {
  private browser: ChromiumManager;
  private config: ReturnType<typeof getPlatformConfig>;

  constructor(browser: ChromiumManager) {
    this.browser = browser;
    this.config = getPlatformConfig('linkedin');
  }

  async login(email: string, password: string): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(this.config.url);
      await this.browser.waitForTimeout(3000);

      const signInButton = await page.$('a[href*="login"]');
      if (signInButton) {
        await signInButton.click();
        await this.browser.waitForTimeout(2000);
      }

      const emailInput = this.config.selectors.loginEmail || 'input[type="email"]';
      const passwordInput = this.config.selectors.loginPassword || 'input[type="password"]';
      
      await this.browser.fill(emailInput, email);
      await this.browser.waitForTimeout(500);

      const passwordField = await page.$(passwordInput);
      if (passwordField) {
        await passwordField.fill(password);
      }

      const submitButton = await page.$('button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
        await this.browser.waitForTimeout(5000);
      }

      const content = await this.browser.getPageContent();
      return !content.includes('Sign in') && !content.includes('sign in');
    } catch (error) {
      console.error('LinkedIn login failed:', error);
      return false;
    }
  }

  async createPost(options: LinkedInPostOptions): Promise<LinkedInPostResult> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate(this.config.url);
      await this.browser.waitForTimeout(3000);

      const startPostButton = await page.$('button:has-text("Start a post")');
      if (startPostButton) {
        await startPostButton.click();
        await this.browser.waitForTimeout(2000);
      }

      const textArea = await page.$('[role="textbox"], .ql-editor, textarea');
      if (!textArea) {
        return { success: false, error: 'Post editor not found' };
      }

      await textArea.click();
      await this.browser.waitForTimeout(500);

      await this.browser.type('[role="textbox"]', options.content, 50);

      const postButton = await page.$('button:has-text("Post")');
      if (postButton) {
        await postButton.click();
        await this.browser.waitForTimeout(3000);
      }

      const currentUrl = page.url();
      const urlMatch = currentUrl.match(/linkedin\.com\/feed\/update\/(\w+)/);

      return {
        success: true,
        url: currentUrl,
        postId: urlMatch ? urlMatch[1] : undefined,
      };
    } catch (error) {
      console.error('LinkedIn post failed:', error);
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
           !content.includes('Join now');
  }
}

export default LinkedInHandler;
