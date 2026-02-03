#!/usr/bin/env node

// Test script for browser-based social media posting
// Tests the /post command functionality

import { SocialMediaBrowserManager } from './src/browser/social_media_browser_manager.js';

async function testBrowserPosting() {
  console.log('🧪 Testing Browser-Based Social Media Posting\n');
  console.log('=' .repeat(60));

  const manager = new SocialMediaBrowserManager({
    credentials: {
      twitter: {
        username: process.env.TWITTER_USERNAME || '',
        password: process.env.TWITTER_PASSWORD || ''
      }
    }
  });

  const testContent = 'Testing browser automation posting from Ultimate Agent! #test #automation';

  try {
    console.log('\n📱 Initializing browser automation...');
    await manager.initializeBrowser();
    console.log('✅ Browser initialized successfully');

    console.log('\n🐦 Testing Twitter posting via browser...');
    console.log('   Content:', testContent);

    const result = await manager.postToTwitterBrowser({
      content: testContent
    });

    console.log('\n' + '=' .repeat(60));
    console.log('📊 RESULT:');
    if (result.success) {
      console.log('✅ ✓ Post successful!');
      console.log('   Tweet ID:', result.tweetId);
      console.log('   URL:', result.url);
    } else {
      console.log('⚠️ Post status:', result.error);
      console.log('\n💡 Possible reasons:');
      console.log('   1. Not logged into Twitter in the browser');
      console.log('   2. TWITTER_USERNAME/TWITTER_PASSWORD not set in .env');
      console.log('   3. Twitter session expired');
      console.log('\n💡 Solutions:');
      console.log('   1. Manually login to Twitter in the browser first');
      console.log('   2. Add credentials to .env file');
      console.log('   3. Or use headless:false to see the browser');
    }

    console.log('\n' + '=' .repeat(60));
    console.log('✅ Test completed!');
    console.log('\n📱 To test via Telegram:');
    console.log('   1. Start the agent: npm start');
    console.log('   2. Send: /post Your message here');
    console.log('   3. Watch the real-time progress!');

    await manager.closeBrowser();

  } catch (error) {
    console.error('\n❌ Test failed:', error);
    await manager.closeBrowser();
    process.exit(1);
  }
}

testBrowserPosting();
