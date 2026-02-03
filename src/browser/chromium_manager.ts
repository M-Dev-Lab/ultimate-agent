import { BrowserContext, Page, firefox, webkit, LaunchOptions, BrowserContextOptions } from 'playwright';
import { chromium } from 'playwright';
import { BrowserConfig, BrowserType, defaultBrowserConfig, getBrowserConfig } from './browser_config.js';
import { autoDetectBrowserPath, getSystemChromeWithProfile } from './system-chrome-detector.js';
import { execSync } from 'child_process';

export class ChromiumManager {
  private browser: BrowserContext | null = null;
  private page: Page | null = null;
  private config: BrowserConfig;
  private browserType: BrowserType;
  private userDataDir: string | null = null;

  constructor(config?: Partial<BrowserConfig>, browserType: BrowserType = 'chromium') {
    this.browserType = browserType;
    const browserDefaults = getBrowserConfig(browserType);
    this.config = { ...defaultBrowserConfig, ...browserDefaults, ...config } as BrowserConfig;
  }

  async launch(): Promise<void> {
    try {
      const launchOptions = this.getLaunchOptions();
      
      console.log('[Browser] Killing any existing Chrome processes...');
      this.killExistingChromeProcesses();
      
      console.log('[Browser] Launching browser with persistent profile...');
      
      if (this.browserType === 'chromium' && this.userDataDir) {
        console.log(`[Browser] Using persistent context with profile: ${this.userDataDir}`);
        
        const contextOptions: BrowserContextOptions = {
          viewport: this.config.viewport,
          userAgent: this.config.userAgent,
          locale: this.config.locale,
          timezoneId: this.config.timezoneId,
          ignoreHTTPSErrors: true,
        };
        
        this.browser = await chromium.launchPersistentContext(
          this.userDataDir,
          {
            ...launchOptions,
            ...contextOptions,
          }
        );
        
        this.page = await this.browser.newPage();
        console.log('[Browser] Persistent context created successfully');
        
      } else if (this.browserType === 'chromium') {
        console.log('[Browser] Launching regular Chromium browser...');
        const chromiumBrowser = await chromium.launch(launchOptions);
        this.browser = await chromiumBrowser.newContext(this.getContextOptions());
        this.page = await this.browser.newPage();
        
      } else if (this.browserType === 'firefox') {
        console.log('[Browser] Launching Firefox browser...');
        const firefoxBrowser = await firefox.launch(launchOptions);
        this.browser = await firefoxBrowser.newContext(this.getContextOptions());
        this.page = await this.browser.newPage();
        
      } else {
        console.log('[Browser] Launching WebKit browser...');
        const webkitBrowser = await webkit.launch(launchOptions);
        this.browser = await webkitBrowser.newContext(this.getContextOptions());
        this.page = await this.browser.newPage();
      }
      
      console.log('[Browser] Browser launched successfully');
      if (this.userDataDir) {
        console.log(`[Browser] Profile loaded: ${this.userDataDir}`);
      }
    } catch (error) {
      console.error(`Failed to launch browser:`, error);
      throw error;
    }
  }

  private killExistingChromeProcesses(): void {
    try {
      execSync('pkill -9 -f "chromium" 2>/dev/null || true');
      execSync('pkill -9 -f "chrome" 2>/dev/null || true');
      execSync('sleep 1');
    } catch (e) {
      // Ignore errors - processes might not exist
    }
  }

  private getLaunchOptions(): LaunchOptions {
    const baseOptions = this.config.launchOptions || {};
    
    let executablePath: string | undefined;
    
    if (this.browserType === 'chromium') {
      const systemChrome = getSystemChromeWithProfile();
      if (systemChrome) {
        executablePath = systemChrome.executablePath;
        this.userDataDir = systemChrome.userDataDir;
        console.log(`[Browser] System Chromium: ${executablePath}`);
        console.log(`[Browser] Profile: ${this.userDataDir}`);
      } else {
        executablePath = autoDetectBrowserPath() || undefined;
        if (executablePath) {
          console.log(`[Browser] System Chromium: ${executablePath}`);
        } else {
          console.log('[Browser] Using Playwright bundled Chromium');
        }
      }
    }
    
    const args = [
      ...(baseOptions.args || []),
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-popup-blocking',
    ];
    
    return {
      ...baseOptions,
      headless: this.config.headless,
      executablePath: executablePath,
      args: args,
    };
  }

  private getContextOptions(): BrowserContextOptions {
    return {
      viewport: this.config.viewport,
      userAgent: this.config.userAgent,
      locale: this.config.locale,
      timezoneId: this.config.timezoneId,
    };
  }

  async navigate(url: string): Promise<void> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }

    await this.page.goto(url, {
      waitUntil: 'domcontentloaded',
      timeout: this.config.timeout,
    });
  }

  async getPage(): Promise<Page> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    return this.page;
  }

  async getContext(): Promise<BrowserContext> {
    if (!this.browser) {
      throw new Error('Browser context not created. Call launch() first.');
    }
    return this.browser;
  }

  async waitForSelector(selector: string, timeout?: number): Promise<void> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    await this.page.waitForSelector(selector, {
      timeout: timeout || this.config.timeout,
      state: 'visible',
    });
  }

  async fill(selector: string, value: string): Promise<void> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    await this.page.fill(selector, value);
  }

  async click(selector: string): Promise<void> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    await this.page.click(selector);
  }

  async type(selector: string, text: string, delay?: number): Promise<void> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    await this.page.type(selector, text, { delay });
  }

  async getPageContent(): Promise<string> {
    if (!this.page) {
      throw new Error('Browser not launched. Call launch() first.');
    }
    return await this.page.content();
  }

  async waitForTimeout(ms: number): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, ms));
  }

  async close(): Promise<void> {
    try {
      if (this.browser) {
        await this.browser.close();
        this.browser = null;
      }
      this.page = null;
      console.log('[Browser] Browser closed');
    } catch (error) {
      console.error('Error closing browser:', error);
    }
  }

  isActive(): boolean {
    return this.browser !== null && this.page !== null;
  }

  getBrowserType(): 'chromium' | 'firefox' | 'webkit' | null {
    return this.browserType;
  }
}

export default ChromiumManager;
