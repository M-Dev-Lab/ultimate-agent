#!/usr/bin/env node

// Test script for browser automation with system browser

import { chromium } from 'playwright';
import { autoDetectBrowserPath } from './src/browser/system-chrome-detector.js';

async function testBrowserLaunch() {
  console.log('🧪 Testing Browser Launch with System Browser\n');
  console.log('=' .repeat(60));

  const browserPath = autoDetectBrowserPath();
  
  if (!browserPath) {
    console.log('❌ No system browser found');
    process.exit(1);
  }
  
  console.log(`\n📱 Launching browser: ${browserPath}`);
  
  try {
    const browser = await chromium.launch({
      executablePath: browserPath,
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
      ]
    });
    
    console.log('✅ Browser launched successfully!');
    
    const page = await browser.newPage();
    await page.goto('https://twitter.com', { waitUntil: 'networkidle' });
    
    console.log('✅ Loaded Twitter successfully!');
    
    const title = await page.title();
    console.log(`📄 Page title: ${title}`);
    
    await browser.close();
    console.log('✅ Browser closed successfully');
    
    console.log('\n' + '=' .repeat(60));
    console.log('✅ All tests passed!');
    console.log('\n💡 The system browser is working correctly!');
    console.log('   The /post command will now use your system browser.');
    
  } catch (error) {
    console.error('❌ Browser test failed:', error);
    process.exit(1);
  }
}

testBrowserLaunch().catch(console.error);
