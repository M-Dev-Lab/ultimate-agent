import { Page } from 'playwright';
import { ChromiumManager } from './chromium_manager.js';

export interface XPostOptions {
  content: string;
  mediaPaths?: string[];
}

export interface XPostResult {
  success: boolean;
  postId?: string;
  url?: string;
  error?: string;
}

export class XHandler {
  private browser: ChromiumManager;
  
  constructor(browser: ChromiumManager) {
    this.browser = browser;
  }

  async login(username: string, password: string): Promise<boolean> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate('https://x.com/i/flow/login');
      await this.browser.waitForTimeout(3000);

      const usernameInput = 'input[autocomplete="username"]';
      const passwordInput = 'input[autocomplete="current-password"]';
      const loginButton = 'button[type="submit"]';

      await this.browser.fill(usernameInput, username);
      await this.browser.click(loginButton);
      await this.browser.waitForTimeout(2000);

      await this.browser.fill(passwordInput, password);
      await this.browser.click(loginButton);
      await this.browser.waitForTimeout(5000);

      const content = await this.browser.getPageContent();
      return !content.includes('login') && !content.includes('error');
    } catch (error) {
      console.error('X login failed:', error);
      return false;
    }
  }

  async createPost(options: XPostOptions): Promise<XPostResult> {
    const page = await this.browser.getPage();
    
    try {
      await this.browser.navigate('https://x.com/home');
      await this.browser.waitForTimeout(3000);

      const postBox = '[role="textbox"]';
      const postButton = '[data-testid="tweetTextarea_0"]';

      const postArea = await page.$(postBox);
      if (!postArea) {
        const content = await this.browser.getPageContent();
        if (content.includes('login') || content.includes('Sign in')) {
          return { success: false, error: 'Not logged in to X' };
        }
        return { success: false, error: 'Post box not found' };
      }

      await postArea.click();
      await this.browser.waitForTimeout(500);

      await this.browser.type(postBox, options.content, 50);

      const submitButton = '[data-testid="tweetButtonInline"]';
      await this.browser.click(submitButton);
      await this.browser.waitForTimeout(3000);

      const currentUrl = page.url();
      const urlMatch = currentUrl.match(/x\.com\/(\w+)/);

      return {
        success: true,
        url: currentUrl,
        postId: urlMatch ? urlMatch[1] : undefined,
      };
    } catch (error) {
      console.error('X post failed:', error);
      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  async checkLoggedIn(): Promise<boolean> {
    await this.browser.navigate('https://x.com/home');
    await this.browser.waitForTimeout(2000);
    
    const content = await this.browser.getPageContent();
    return !content.includes('login') && 
           !content.includes('Sign in') && 
           !content.includes('Log in');
  }
}

export default XHandler;
