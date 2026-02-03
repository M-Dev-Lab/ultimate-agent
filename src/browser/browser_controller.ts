/*
  Enhanced Browser Controller for AI Agent
  Provides robust browser automation and navigation for completing tasks
*/

import { chromium, Firefox, webkit, Browser, Page, BrowserContext } from 'playwright';

export interface BrowserTask {
  id: string;
  type: 'navigate' | 'click' | 'type' | 'extract' | 'screenshot' | 'scroll' | 'wait' | 'evaluate';
  target?: string;
  value?: string;
  timeout?: number;
  selector?: string;
}

export interface TaskResult {
  success: boolean;
  taskId: string;
  data?: any;
  error?: string;
  screenshot?: string;
}

export interface BrowserConfig {
  headless: boolean;
  browserType: 'chromium' | 'firefox' | 'webkit';
  viewport: { width: number; height: number };
  userAgent: string;
  timeout: number;
}

export class BrowserController {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private currentUrl: string = '';
  private config: BrowserConfig;
  private taskHistory: TaskResult[] = [];
  private isInitialized: boolean = false;

  constructor(config?: Partial<BrowserConfig>) {
    this.config = {
      headless: config?.headless ?? false,
      browserType: config?.browserType ?? 'chromium',
      viewport: config?.viewport ?? { width: 1920, height: 1080 },
      userAgent: config?.userAgent ?? 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      timeout: config?.timeout ?? 60000
    };
  }

  async initialize(): Promise<boolean> {
    if (this.isInitialized) {
      return true;
    }

    try {
      console.log(`🌐 Initializing ${this.config.browserType} browser...`);

      // Launch browser based on type
      switch (this.config.browserType) {
        case 'chromium':
          this.browser = await chromium.launch({
            headless: this.config.headless,
            args: [
              '--no-sandbox',
              '--disable-setuid-sandbox',
              '--disable-dev-shm-usage',
              '--disable-gpu',
              '--disable-web-security',
              '--allow-running-insecure-content',
              '--disable-features=IsolateOrigins,site-per-process'
            ]
          });
          break;
        case 'firefox':
          this.browser = await Firefox.launch({
            headless: this.config.headless
          });
          break;
        case 'webkit':
          this.browser = await webkit.launch({
            headless: this.config.headless
          });
          break;
      }

      if (!this.browser) {
        throw new Error('Failed to launch browser');
      }

      // Create context with stealth settings
      this.context = await this.browser.newContext({
        viewport: this.config.viewport,
        userAgent: this.config.userAgent,
        ignoreHTTPSErrors: true,
        javaScriptEnabled: true,
        locale: 'en-US',
        timezoneId: 'America/New_York'
      });

      // Create page
      this.page = await this.context.newPage();
      
      // Set up error handlers
      this.page.on('pageerror', error => {
        console.error('Page error:', error.message);
      });

      this.page.on('console', msg => {
        if (msg.type() === 'error') {
          console.error('Console error:', msg.text());
        }
      });

      this.isInitialized = true;
      console.log('✅ Browser initialized successfully');
      return true;

    } catch (error: any) {
      console.error('Failed to initialize browser:', error);
      return false;
    }
  }

  async executeTask(task: BrowserTask): Promise<TaskResult> {
    if (!this.isInitialized || !this.page) {
      return {
        success: false,
        taskId: task.id,
        error: 'Browser not initialized'
      };
    }

    try {
      let result: TaskResult = {
        success: true,
        taskId: task.id
      };

      switch (task.type) {
        case 'navigate':
          await this.navigateTo(task.target || '', task.timeout);
          break;

        case 'click':
          if (task.selector) {
            await this.click(task.selector, task.timeout);
          }
          break;

        case 'type':
          if (task.selector && task.value) {
            await this.type(task.selector, task.value, task.timeout);
          }
          break;

        case 'extract':
          if (task.selector) {
            result.data = await this.extractText(task.selector);
          }
          break;

        case 'screenshot':
          result.screenshot = await this.takeScreenshot(task.selector);
          break;

        case 'scroll':
          await this.scroll(task.value || 'down', task.selector);
          break;

        case 'wait':
          await this.wait(task.timeout || 1000);
          break;

        case 'evaluate':
          if (task.value) {
            result.data = await this.evaluateJavaScript(task.value);
          }
          break;

        default:
          result = {
            success: false,
            taskId: task.id,
            error: `Unknown task type: ${task.type}`
          };
      }

      this.taskHistory.push(result);
      return result;

    } catch (error: any) {
      const result: TaskResult = {
        success: false,
        taskId: task.id,
        error: error.message || 'Unknown error'
      };
      this.taskHistory.push(result);
      return result;
    }
  }

  async executeTaskSequence(tasks: BrowserTask[]): Promise<TaskResult[]> {
    const results: TaskResult[] = [];

    for (const task of tasks) {
      const result = await this.executeTask(task);
      results.push(result);

      if (!result.success && task.type !== 'navigate') {
        // Continue on failure but log it
        console.warn(`Task ${task.id} failed: ${result.error}`);
      }
    }

    return results;
  }

  // Navigation methods
  async navigateTo(url: string, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    console.log(`📍 Navigating to: ${url}`);
    await this.page.goto(url, {
      waitUntil: 'networkidle',
      timeout: timeout || this.config.timeout
    });

    this.currentUrl = this.page.url();
    console.log(`✅ Navigated to: ${this.currentUrl}`);
  }

  async navigateWithRetry(url: string, maxRetries: number = 3): Promise<boolean> {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await this.navigateTo(url);
        return true;
      } catch (error: any) {
        console.warn(`Navigation attempt ${attempt} failed: ${error.message}`);
        if (attempt < maxRetries) {
          await this.wait(2000 * attempt); // Exponential backoff
        }
      }
    }
    return false;
  }

  async goBack(): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');
    await this.page.goBack();
  }

  async goForward(): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');
    await this.page.goForward();
  }

  async reload(): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');
    await this.page.reload({ waitUntil: 'networkidle' });
  }

  // Interaction methods
  async click(selector: string, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    console.log(`👆 Clicking: ${selector}`);
    await this.page.click(selector, {
      timeout: timeout || this.config.timeout,
      force: false
    });
  }

  async doubleClick(selector: string, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    console.log(`👆👆 Double clicking: ${selector}`);
    await this.page.dblclick(selector, {
      timeout: timeout || this.config.timeout
    });
  }

  async type(selector: string, text: string, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    console.log(`⌨️  Typing in ${selector}: "${text.substring(0, 50)}..."`);
    await this.page.fill(selector, text);
  }

  async pressKey(key: string): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');
    await this.page.keyboard.press(key);
  }

  // Extraction methods
  async extractText(selector: string): Promise<string> {
    if (!this.page) throw new Error('Page not initialized');

    const element = await this.page.$(selector);
    if (!element) {
      throw new Error(`Element not found: ${selector}`);
    }

    return await element.textContent() || '';
  }

  async extractAllText(selector: string): Promise<string[]> {
    if (!this.page) throw new Error('Page not initialized');

    const elements = await this.page.$$(selector);
    const texts: string[] = [];

    for (const element of elements) {
      const text = await element.textContent();
      if (text) texts.push(text);
    }

    return texts;
  }

  async extractAttribute(selector: string, attribute: string): Promise<string | null> {
    if (!this.page) throw new Error('Page not initialized');

    const element = await this.page.$(selector);
    if (!element) {
      throw new Error(`Element not found: ${selector}`);
    }

    return await element.getAttribute(attribute);
  }

  // Screenshot and visual methods
  async takeScreenshot(selector?: string): Promise<string> {
    if (!this.page) throw new Error('Page not initialized');

    const timestamp = Date.now();
    const filename = `/tmp/screenshot-${timestamp}.png`;

    if (selector) {
      const element = await this.page.$(selector);
      if (element) {
        await element.screenshot({ path: filename });
      }
    } else {
      await this.page.screenshot({ path: filename, fullPage: false });
    }

    console.log(`📸 Screenshot saved: ${filename}`);
    return filename;
  }

  async scroll(direction: 'up' | 'down' | 'top' | 'bottom', selector?: string): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    if (selector) {
      const element = await this.page.$(selector);
      if (element) {
        await element.scrollIntoViewIfNeeded();
      }
    } else {
      switch (direction) {
        case 'up':
          await this.page.evaluate(() => window.scrollBy(0, -500));
          break;
        case 'down':
          await this.page.evaluate(() => window.scrollBy(0, 500));
          break;
        case 'top':
          await this.page.evaluate(() => window.scrollTo(0, 0));
          break;
        case 'bottom':
          await this.page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          break;
      }
    }
  }

  // JavaScript execution
  async evaluateJavaScript(script: string): Promise<any> {
    if (!this.page) throw new Error('Page not initialized');

    console.log(`📜 Evaluating JavaScript: ${script.substring(0, 50)}...`);
    return await this.page.evaluate(script);
  }

  // Waiting methods
  async wait(milliseconds: number): Promise<void> {
    console.log(`⏳ Waiting ${milliseconds}ms...`);
    await new Promise(resolve => setTimeout(resolve, milliseconds));
  }

  async waitForSelector(selector: string, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    await this.page.waitForSelector(selector, {
      timeout: timeout || this.config.timeout
    });
  }

  async waitForNavigation(timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    await this.page.waitForLoadState('networkidle', {
      timeout: timeout || this.config.timeout
    });
  }

  async waitForURL(urlPattern: string | RegExp, timeout?: number): Promise<void> {
    if (!this.page) throw new Error('Page not initialized');

    await this.page.waitForURL(urlPattern, {
      timeout: timeout || this.config.timeout
    });
  }

  // Utility methods
  getCurrentURL(): string {
    return this.currentUrl;
  }

  getPageTitle(): string {
    return this.page?.title() || '';
  }

  getTaskHistory(): TaskResult[] {
    return [...this.taskHistory];
  }

  clearTaskHistory(): void {
    this.taskHistory = [];
  }

  isBrowserActive(): boolean {
    return this.browser !== null && this.isInitialized;
  }

  // Session management
  async close(): Promise<void> {
    if (this.page) {
      await this.page.close();
      this.page = null;
    }

    if (this.context) {
      await this.context.close();
      this.context = null;
    }

    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }

    this.isInitialized = false;
    console.log('🌐 Browser closed');
  }

  // Convenience methods for common tasks
  async loginToWebsite(url: string, usernameSelector: string, passwordSelector: string, 
                      username: string, password: string, submitSelector?: string): Promise<boolean> {
    try {
      await this.navigateTo(url);
      await this.waitForSelector(usernameSelector);
      await this.type(usernameSelector, username);
      await this.type(passwordSelector, password);

      if (submitSelector) {
        await this.click(submitSelector);
        await this.waitForNavigation();
      }

      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }

  async fillForm(formData: Record<string, { selector: string; value: string }>): Promise<void> {
    for (const [key, field] of Object.entries(formData)) {
      console.log(`📝 Filling ${key}: ${field.selector}`);
      await this.waitForSelector(field.selector);
      await this.type(field.selector, field.value);
    }
  }

  async scrapeTable(tableSelector: string): Promise<Record<string, string>[]> {
    const rows = await this.page?.$$(`${tableSelector} tr`) || [];
    const data: Record<string, string>[] = [];

    for (const row of rows) {
      const cells = await row.$$('td, th');
      if (cells.length >= 2) {
        const key = await cells[0].textContent();
        const value = await cells[1].textContent();
        if (key && value) {
          data.push({ [key.trim()]: value.trim() });
        }
      }
    }

    return data;
  }
}

export default BrowserController;
