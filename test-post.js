#!/usr/bin/env node

// Test script for social media posting functionality
// Run this to verify the /post command works correctly

import { SocialMediaManager } from './dist/social/social_media_manager.js';

async function testSocialMediaPost() {
  console.log('🧪 Testing Social Media Posting Functionality\n');
  console.log('=' .repeat(60));

  const manager = new SocialMediaManager();

  const testContent = 'Testing the new social media posting feature! #test #coding';

  try {
    console.log('\n📝 Test Content:', testContent);
    console.log('\n📊 Step 1: Optimizing content for virality...');
    
    const optimized = await manager.optimizeForVirality(testContent, 'twitter');
    console.log('   ✓ Virality Score:', optimized.score);
    console.log('   ✓ Engagement Prediction:', optimized.engagementPrediction);
    console.log('   ✓ Suggestions:', optimized.suggestions.join('; '));

    console.log('\n🏷️ Step 2: Generating hashtags...');
    const hashtags = await manager.generateHashtags(testContent, 'twitter');
    console.log('   ✓ Generated Hashtags:', hashtags.join(' '));

    const finalContent = `${testContent}\n\n${optimized.suggestions.join(' ')}\n\n${hashtags.join(' ')}`;
    console.log('\n📄 Final Content:');
    console.log('─' .repeat(60));
    console.log(finalContent);
    console.log('─' .repeat(60));

    console.log('\n🐦 Step 3: Attempting to post to Twitter...');
    console.log('   Note: This will fail if Twitter API credentials are not configured');
    console.log('   Check .env file for TWITTER_ configuration variables\n');

    const result = await manager.postToTwitter(finalContent);
    
    if (result.success) {
      console.log('✅ ✓ Twitter post successful!');
      console.log('   Tweet ID:', result.tweetId);
      console.log('   URL: https://twitter.com/i/web/status/' + result.tweetId);
    } else {
      console.log('⚠️ Twitter post failed (expected if no credentials):');
      console.log('   Error:', result.error);
      console.log('\n💡 To enable Twitter posting, add these to .env:');
      console.log('   TWITTER_API_KEY=your_api_key');
      console.log('   TWITTER_API_SECRET=your_api_secret');
      console.log('   TWITTER_ACCESS_TOKEN=your_access_token');
      console.log('   TWITTER_ACCESS_SECRET=your_access_secret');
      console.log('   TWITTER_BEARER_TOKEN=your_bearer_token');
    }

    console.log('\n' + '=' .repeat(60));
    console.log('✅ Test completed successfully!');
    console.log('\n📱 To test the Telegram /post command:');
    console.log('   1. Start the agent: npm start');
    console.log('   2. Send: /post Your message here');
    console.log('   3. Watch the real-time progress updates!');

  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exit(1);
  }
}

testSocialMediaPost();
