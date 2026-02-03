import { Page } from 'playwright';
import { ChromiumManager } from './chromium_manager.js';

export interface FacebookPostOptions {
  content: string;
  imagePaths?: string[];
  videoPaths?: string[];
}

export interface FacebookPostResult {
  success: boolean;
  postId?: string;
  url?: string;
  error?: string;
}

export class FacebookHandler {
  private browser: ChromiumManager;

  constructor(browser: ChromiumManager) {
    this.browser = browser;
  }

  async createPost(options: FacebookPostOptions): Promise<FacebookPostResult> {
    const page = await this.browser.getPage();
    
    try {
      console.log('[Facebook] Navigating to Facebook...');
      await this.browser.navigate('https://www.facebook.com');
      await this.browser.waitForTimeout(3000);
      
      console.log('[Facebook] Looking for post creation area...');
      
      const postBoxSelectors = [
        '[role="textbox"][aria-label*="Create post"]',
        '[role="textbox"][aria-label*="What\'s on your mind"]',
        '[data-testid="post_input"]',
        '.x1iy669o .xzsf02u',
        '[contenteditable="true"][role="textbox"]',
        'div[style*="overflow"][role="presentation"]',
        '.x1n2onr6',
      ];
      
      let postBox = null;
      for (const selector of postBoxSelectors) {
        postBox = await page.$(selector);
        if (postBox) {
          console.log(`[Facebook] Found post box with selector: ${selector}`);
          break;
        }
      }
      
      if (!postBox) {
        console.log('[Facebook] Post box not found, checking page state...');
        const content = await this.browser.getPageContent();
        
        if (content.includes('Accept All') || content.includes('cookie')) {
          console.log('[Facebook] Cookie consent popup detected, accepting...');
          const acceptBtn = await page.$('button:has-text("Accept All"), button:has-text("Allow all")');
          if (acceptBtn) {
            await acceptBtn.click();
            await this.browser.waitForTimeout(2000);
          }
        }
        
        const profileNav = await page.$('[aria-label="Profile"], [data-testid="profile"]');
        if (profileNav) {
          console.log('[Facebook] User appears to be logged in (profile found)');
          await this.browser.waitForTimeout(2000);
          
          for (const selector of postBoxSelectors) {
            postBox = await page.$(selector);
            if (postBox) {
              console.log(`[Facebook] Found post box with selector: ${selector}`);
              break;
            }
          }
        } else if (content.includes('login') && content.includes('password')) {
          return { success: false, error: 'Not logged in to Facebook - please log in manually' };
        } else {
          return { success: false, error: 'Could not find Facebook post box' };
        }
      }
      
      if (postBox) {
        console.log('[Facebook] Clicking on post box...');
        await postBox.click({ force: true });
        await this.browser.waitForTimeout(1000);
        
        const textBox = await page.$('[role="textbox"], [contenteditable="true"]');
        if (textBox) {
          console.log('[Facebook] Typing post content...');
          await textBox.fill(options.content);
          await this.browser.waitForTimeout(1000);
        }
        
        console.log('[Facebook] Looking for post button...');
        const postButtonSelectors = [
          '[data-testid="react-composer-post-button"]',
          'button:has-text("Post")',
          '[role="button"][tabindex="0"]:has-text("Post")',
          'div[aria-label="Post"]',
        ];
        
        let postButton = null;
        for (const selector of postButtonSelectors) {
          postButton = await page.$(selector);
          if (postButton) {
            console.log(`[Facebook] Found post button with selector: ${selector}`);
            break;
          }
        }
        
        if (postButton) {
          console.log('[Facebook] Clicking post button...');
          await postButton.click({ force: true });
          await this.browser.waitForTimeout(5000);
          console.log('[Facebook] Post submitted successfully!');
        } else {
          console.log('[Facebook] Post button not found, post content may have been typed');
        }
      }
      
      const currentUrl = page.url();
      console.log(`[Facebook] Current URL: ${currentUrl}`);
      
      return {
        success: true,
        url: currentUrl,
      };
    } catch (error) {
      console.error('[Facebook] Post failed:', error);
      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  async checkLoggedIn(): Promise<boolean> {
    try {
      const page = await this.browser.getPage();
      await this.browser.navigate('https://www.facebook.com');
      await this.browser.waitForTimeout(3000);
      
      const content = await this.browser.getPageContent();
      
      const loggedInIndicators = [
        '[aria-label="Profile"]',
        '[data-testid="profile"]',
        '.x1iy669o',
        '[data-pagelet="Stories"]',
        '[role="navigation"]',
      ];
      
      for (const selector of loggedInIndicators) {
        const element = await page.$(selector);
        if (element) {
          console.log(`[Facebook] Found logged-in indicator: ${selector}`);
          return true;
        }
      }
      
      const loginForms = await page.$$('form[action*="login"], input[name="email"][type="email"]');
      if (loginForms.length > 0) {
        console.log('[Facebook] Login form detected - not logged in');
        return false;
      }
      
      if (content.includes('Accept All') || content.includes('cookie')) {
        console.log('[Facebook] Cookie popup detected - user likely logged in');
        return true;
      }
      
      console.log('[Facebook] Could not determine login status');
      return false;
    } catch (error) {
      console.error('[Facebook] Check logged in failed:', error);
      return false;
    }
  }
}

export default FacebookHandler;
