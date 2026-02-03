import { SocialMediaBrowserManager, SocialMediaConfig, FacebookPostOptions, defaultBrowserConfig } from '../src/browser/index.js';

const config: SocialMediaConfig = {
  browser: {
    ...defaultBrowserConfig,
    headless: true,
    stealth: true,
    enableHumanSimulation: true,
  },
  credentials: {
    facebook: {
      email: process.env.FACEBOOK_EMAIL || '',
      password: process.env.FACEBOOK_PASSWORD || '',
    },
    instagram: {
      username: process.env.INSTAGRAM_USERNAME || '',
      password: process.env.INSTAGRAM_PASSWORD || '',
    },
    tiktok: {
      username: process.env.TIKTOK_USERNAME || '',
      password: process.env.TIKTOK_PASSWORD || '',
    },
    youtube: {
      email: process.env.YOUTUBE_EMAIL || '',
      password: process.env.YOUTUBE_PASSWORD || '',
      recoveryEmail: process.env.YOUTUBE_RECOVERY_EMAIL || '',
    },
  },
  useCloudModels: true,
};

async function example() {
  console.log('=== Social Media Browser Automation with Cloud Models ===\n');
  console.log('Model Priority: Qwen3 Coder 480B > DeepSeek V3.1 > GPT-OSS 120B > Local Ollama\n');

  const manager = new SocialMediaBrowserManager(config);

  console.log('1. Checking model status...');
  const modelStatus = await manager.getModelStatus();
  console.log(`   Cloud available: ${modelStatus.cloud}`);
  console.log(`   Local available: ${modelStatus.local}`);
  console.log(`   Current model: ${modelStatus.current} (${modelStatus.model})`);
  console.log('');

  console.log('2. Testing virality optimization (using cloud models)...');
  const virality = await manager.optimizeForVirality(
    'Check out my new product launch! #tech #innovation',
    'twitter'
  );
  console.log(`   Virality score: ${virality.score}/100`);
  console.log(`   Engagement prediction: ${virality.engagementPrediction}`);
  console.log(`   Suggestions: ${virality.suggestions.slice(0, 2).join(', ')}`);
  console.log('');

  console.log('3. Generating hashtags...');
  const hashtags = await manager.generateHashtags(
    'Building amazing applications with AI',
    'linkedin'
  );
  console.log(`   Hashtags: ${hashtags.join(' ')}`);
  console.log('');

  console.log('4. Generating viral content for different platforms...');
  
  const viralTwitter = await manager.generateViralPost('AI automation tools', 'twitter');
  console.log('   Twitter post:', viralTwitter.content.substring(0, 80) + '...');
  console.log(`   Virality score: ${viralTwitter.viralityScore}`);
  console.log('');

  const viralInstagram = await manager.generateViralPost('Travel photography', 'instagram');
  console.log('   Instagram caption:', viralInstagram.content.substring(0, 80) + '...');
  console.log(`   Virality score: ${viralInstagram.viralityScore}`);
  console.log('');

  const viralYouTube = await manager.generateViralPost('Python tutorial', 'youtube');
  try {
    const ytContent = typeof viralYouTube.content === 'string' 
      ? JSON.parse(viralYouTube.content) 
      : viralYouTube.content;
    console.log('   YouTube title:', ytContent.title || viralYouTube.content);
    console.log('   YouTube tags:', (ytContent.tags || []).slice(0, 3).join(', '));
  } catch {
    console.log('   YouTube content:', viralYouTube.content.substring(0, 80) + '...');
  }
  console.log(`   Virality score: ${viralYouTube.viralityScore}`);
  console.log('');

  console.log('5. Scheduling browser-based posts...');
  const scheduledTime = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const facebookPostId = manager.scheduleBrowserPost(
    'facebook',
    {
      content: 'Scheduled post via browser automation!',
      imagePaths: [],
    } as FacebookPostOptions,
    scheduledTime
  );
  console.log(`   Scheduled Facebook post ID: ${facebookPostId.substring(0, 20)}...`);
  console.log('');

  console.log('6. Getting post stats...');
  const stats = manager.getStats();
  console.log(`   Total scheduled posts: ${stats.totalScheduled}`);
  console.log(`   By platform:`, stats.byPlatform);
  console.log('');

  console.log('7. Closing browser...');
  await manager.closeBrowser();
  console.log('Done!');
}

example().catch(console.error);
