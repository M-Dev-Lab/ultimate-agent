import { BrowserContextOptions, LaunchOptions } from 'playwright';

export type BrowserType = 'chromium' | 'firefox' | 'webkit';

export interface BrowserConfig {
  browserType: BrowserType;
  launchOptions: LaunchOptions;
  contextOptions: BrowserContextOptions;
  stealth: boolean;
  headless: boolean;
  timeout: number;
  viewport: {
    width: number;
    height: number;
  };
  userAgent: string;
  locale: string;
  timezoneId: string;
  enableHumanSimulation: boolean;
  randomDelayRange: {
    min: number;
    max: number;
  };
}

export interface PlatformCredentials {
  facebook?: {
    email: string;
    password: string;
  };
  instagram?: {
    username: string;
    password: string;
  };
  tiktok?: {
    username: string;
    password: string;
  };
  youtube?: {
    email: string;
    password: string;
    recoveryEmail?: string;
  };
  x?: {
    username: string;
    password: string;
  };
  linkedin?: {
    email: string;
    password: string;
  };
}

export interface PlatformSelectors {
  postBox?: string;
  postButton: string;
  fileInput?: string;
  nextButton?: string;
  shareButton?: string;
  captionBox?: string;
  loginEmail?: string;
  loginUsername?: string;
  loginPassword: string;
  loginButton?: string;
  uploadButton?: string;
  titleBox?: string;
  descriptionBox?: string;
  confirmPost?: string;
  publicButton?: string;
  signInButton?: string;
  cookieAccept?: string;
}

export interface PlatformConfig {
  url: string;
  selectors: PlatformSelectors;
  maxPostLength?: number;
  uploadSupport: boolean;
  videoMaxSize?: number;
  imageMaxSize?: number;
  videoDuration?: {
    min: number;
    max: number;
  };
  aspectRatios?: string[];
  thumbnailSupport?: boolean;
}

export const chromiumStealthArgs = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
  '--disable-gpu',
  '--disable-web-security',
  '--disable-features=IsolateOrigins,site-per-process',
  '--allow-running-insecure-content',
  '--enable-features=NetworkServiceInProcess2',
  '--window-size=1920,1080',
  '--start-maximized',
  '--disable-blink-features=AutomationControlled',
  '--disable-infobars',
  '--disable-extensions',
  '--disable-background-networking',
  '--disable-sync',
  '--disable-translate',
  '--metrics-recording-only',
  '--mute-audio',
  '--no-first-run',
  '--safebrowsing-disable-auto-update',
  '--hide-scrollbars',
  '--disable-ipc-flooding-protection',
  '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows',
  '--disable加速-2d-canvas',
  '--ignore-gpu-blocklist',
  '--enable-logging',
  '--v=1',
];

export const firefoxPrefs = {
  'network.http.max-persistent-connections-per-server': 6,
  'browser.contentblocking.category': 'strict',
  'privacy.resistFingerprinting': false,
  'dom.webdriver.enabled': false,
  'media.peerconnection.enabled': true,
  'permissions.default.desktop-notification': 1,
};

export const defaultBrowserConfig: BrowserConfig = {
  browserType: 'chromium',
  launchOptions: {
    headless: false,
    args: chromiumStealthArgs,
  },
  contextOptions: {
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    javaScriptEnabled: true,
    locale: 'en-US',
    timezoneId: 'America/New_York',
    permissions: [],
    reducedMotion: 'no-preference',
    colorScheme: 'light',
  },
  stealth: false,
  headless: false,
  timeout: 60000,
  viewport: {
    width: 1920,
    height: 1080,
  },
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  locale: 'en-US',
  timezoneId: 'America/New_York',
  enableHumanSimulation: true,
  randomDelayRange: {
    min: 500,
    max: 2000,
  },
};

export const browserConfigs: Record<BrowserType, Partial<BrowserConfig>> = {
  chromium: {
    launchOptions: {
      headless: true,
      args: chromiumStealthArgs,
    },
    contextOptions: {
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
      colorScheme: 'light',
    },
  },
  firefox: {
    launchOptions: {
      headless: true,
      firefoxUserPrefs: firefoxPrefs,
    },
    contextOptions: {
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
    },
  },
  webkit: {
    launchOptions: {
      headless: true,
    },
    contextOptions: {
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
    },
  },
};

export const platformConfigs: Record<string, PlatformConfig> = {
  facebook: {
    url: 'https://www.facebook.com',
    selectors: {
      postBox: '[role="textbox"], [contenteditable="true"]',
      postButton: '[data-testid="react-composer-post-button"], [aria-label="Post"], button[type="submit"]:has-text("Post")',
      loginEmail: '#email, input[name="email"]',
      loginPassword: '#pass, input[name="pass"]',
      loginButton: 'button[name="login"], button[type="submit"]:has-text("Log in")',
      confirmPost: '[data-testid="react-composer-post-button"]',
      cookieAccept: '[data-testid="cookie-policy-dialog-accept-button"], button:has-text("Accept all")',
    },
    maxPostLength: 63206,
    uploadSupport: true,
    videoMaxSize: 1024 * 1024 * 1024 * 4,
    imageMaxSize: 1024 * 1024 * 8,
  },
  instagram: {
    url: 'https://www.instagram.com',
    selectors: {
      postButton: 'svg[aria-label="New post"], [aria-label="New post"]',
      fileInput: 'input[type="file"]',
      nextButton: 'button:has-text("Next")',
      shareButton: 'button:has-text("Share")',
      captionBox: '[contenteditable="true"]',
      loginUsername: 'input[name="username"]',
      loginPassword: 'input[name="password"]',
      loginButton: 'button[type="submit"]',
      cookieAccept: 'button:has-text("Accept all"), button:has-text("Allow all")',
    },
    maxPostLength: 2200,
    uploadSupport: true,
    videoMaxSize: 1024 * 1024 * 650,
    imageMaxSize: 1024 * 1024 * 8,
    aspectRatios: ['1:1', '4:5', '9:16'],
  },
  tiktok: {
    url: 'https://www.tiktok.com',
    selectors: {
      uploadButton: '[data-e2e="upload-icon"]',
      fileInput: 'input[type="file"]',
      nextButton: 'button:has-text("Next")',
      postButton: 'button:has-text("Post")',
      captionBox: '[contenteditable="true"]',
      loginUsername: 'input[placeholder*="username"], input[name="username"]',
      loginPassword: 'input[placeholder*="password"], input[name="password"]',
      loginButton: 'button[type="submit"]',
      cookieAccept: 'button:has-text("Accept all"), button:has-text("Allow all")',
    },
    maxPostLength: 2200,
    uploadSupport: true,
    videoMaxSize: 1024 * 1024 * 287,
    imageMaxSize: 0,
    videoDuration: {
      min: 3,
      max: 180,
    },
  },
  youtube: {
    url: 'https://www.youtube.com',
    selectors: {
      uploadButton: '#button[aria-label="Create"], [aria-label="Create"]',
      fileInput: 'input[type="file"]',
      titleBox: '#textbox, [aria-label="Title"]',
      descriptionBox: '#description-textarea, [aria-label="Description"]',
      nextButton: 'button:has-text("Next")',
      publicButton: 'button:contains("Public")',
      postButton: 'button:has-text("Publish")',
      signInButton: 'a[href="/signin"]',
      loginEmail: 'input[type="email"], input[name="identifier"]',
      loginPassword: 'input[type="password"], input[name="password"]',
      loginButton: 'button[type="submit"]',
      cookieAccept: 'button:has-text("I agree"), button:has-text("Accept all")',
    },
    uploadSupport: true,
    videoMaxSize: 1024 * 1024 * 128,
    videoDuration: {
      min: 1,
      max: 12 * 60 * 60,
    },
    thumbnailSupport: true,
  },
  x: {
    url: 'https://x.com',
    selectors: {
      postBox: '[role="textbox"]',
      postButton: '[data-testid="tweetTextarea_0"]',
      loginUsername: 'input[autocomplete="username"]',
      loginPassword: 'input[autocomplete="current-password"]',
      loginButton: 'button[type="submit"]',
      cookieAccept: 'button:has-text("Accept all"), [role="button"]:has-text("Accept")',
    },
    maxPostLength: 280,
    uploadSupport: true,
    imageMaxSize: 1024 * 1024 * 5,
  },
  linkedin: {
    url: 'https://www.linkedin.com',
    selectors: {
      postBox: '[role="textbox"], .ql-editor',
      postButton: 'button:has-text("Post")',
      loginEmail: 'input[type="email"], input[name="session_key"]',
      loginPassword: 'input[type="password"], input[name="session_password"]',
      loginButton: 'button[type="submit"]',
      cookieAccept: 'button:has-text("Accept all"), [data-testid="cookie-policy-banner-accept"]',
    },
    maxPostLength: 3000,
    uploadSupport: true,
    imageMaxSize: 1024 * 1024 * 5,
  },
};

export function getPlatformConfig(platform: string): PlatformConfig {
  const config = platformConfigs[platform];
  if (!config) {
    throw new Error(`Unknown platform: ${platform}`);
  }
  return config;
}

export function getBrowserConfig(type: BrowserType): Partial<BrowserConfig> {
  return browserConfigs[type] || browserConfigs.chromium;
}
