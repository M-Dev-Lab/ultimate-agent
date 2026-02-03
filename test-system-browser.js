#!/usr/bin/env node

// Test script for system browser detection

import { getSystemChromeExecutable, autoDetectBrowserPath } from './src/browser/system-chrome-detector.js';

async function testBrowserDetection() {
  console.log('🧪 Testing System Browser Detection\n');
  console.log('=' .repeat(60));

  console.log('\n📱 Detecting system Chrome/Chromium...');
  
  const browser = getSystemChromeExecutable();
  
  console.log('\n' + '=' .repeat(60));
  console.log('📊 RESULT:');
  
  if (browser) {
    console.log('✅ System browser found!');
    console.log(`   Kind: ${browser.kind}`);
    console.log(`   Path: ${browser.path}`);
  } else {
    console.log('⚠️ No system browser detected');
    console.log('\n💡 To use system browser:');
    console.log('   1. Install Chrome/Chromium/Brave/Edge');
    console.log('   2. Make it your default browser');
    console.log('   3. Or set explicitly in .env: BROWSER_EXECUTABLE_PATH=/path/to/browser');
  }
  
  const autoPath = autoDetectBrowserPath();
  console.log(`\n🔍 Auto-detected path: ${autoPath || 'None'}`);
  
  console.log('\n' + '=' .repeat(60));
  console.log('✅ Test completed!');
  
  console.log('\n📱 To test the /post command:');
  console.log('   1. Start the agent: npm start');
  console.log('   2. Send: /post Your message here');
  console.log('   3. The agent will use your system browser!');
}

testBrowserDetection().catch(console.error);
