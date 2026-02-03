#!/usr/bin/env node

// Simple test to verify system browser works

import { chromium } from 'playwright';
import { autoDetectBrowserPath } from './src/browser/system-chrome-detector.js';

async function simpleTest() {
  console.log('🧪 Simple Browser Test\n');
  
  const browserPath = autoDetectBrowserPath();
  
  if (!browserPath) {
    console.log('❌ No browser found');
    process.exit(1);
  }
  
  console.log(`Using browser: ${browserPath}\n`);
  
  const browser = await chromium.launch({
    executablePath: browserPath,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox', 
      '--disable-dev-shm-usage',
      '--disable-gpu'
    ]
  });
  
  console.log('✅ Browser launched');
  
  const page = await browser.newPage();
  console.log('✅ Page created');
  
  await page.goto('https://example.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
  console.log('✅ Page loaded');
  
  const title = await page.title();
  console.log(`✅ Title: ${title}`);
  
  await browser.close();
  console.log('✅ Browser closed');
  
  console.log('\n🎉 All basic tests passed!');
  console.log('The system browser integration is working correctly.');
}

simpleTest().catch(err => {
  console.error('❌ Test failed:', err.message);
  process.exit(1);
});
