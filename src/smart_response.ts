/*
  Smart Response System for Telegram Bot
  Generates contextual, personality-driven responses with suggestions
 */

import { Markup } from 'telegraf';

interface SmartResponseHooks {
  success: string[];
  failure: string[];
}

interface ActionHooks {
  [action: string]: SmartResponseHooks;
}

interface SmartSuggestions {
  label: string;
  callback: string;
}

export class SmartResponse {
  private hooks: ActionHooks;
  private memory: any = null;

  constructor() {
    this.hooks = this.initializeHooks();
  }

  private initializeHooks(): ActionHooks {
    return {
      'build': {
        success: [
          "🦞 Built it!",
          "⚡ Done and done!",
          "🔥 That was quick!",
          "✅ Project ready!",
          "🚀 Built and ready to ship!"
        ],
        failure: [
          "🤔 Hit a snag...",
          "⚠️ Hold up, found an issue...",
          "🔧 Need to fix something first...",
          "❌ Build failed, let me explain..."
        ]
      },
      'deploy': {
        success: [
          "🚀 Deployed!",
          "✅ Live now!",
          "🌍 It's out there!",
          "📡 Pushed to production!",
          "🎯 Deploy successful!"
        ],
        failure: [
          "⚠️ Deploy failed...",
          "🔧 Deployment issue detected...",
          "❌ Couldn't deploy, here's why...",
          "🚫 Production deployment blocked..."
        ]
      },
      'post': {
        success: [
          "📱 Posted!",
          "✅ It's live!",
          "🎯 Shared across platforms!",
          "📡 Post published!",
          "🔥 Content is out!"
        ],
        failure: [
          "⚠️ Couldn't post...",
          "🔧 Posting failed...",
          "❌ Social media error...",
          "🚫 Post blocked..."
        ]
      },
      'fix': {
        success: [
          "🔧 Fixed!",
          "✅ Bug squashed!",
          "🐛 Issue resolved!",
          "⚡ All good now!",
          "🎯 Fixed and tested!"
        ],
        failure: [
          "🤔 Still debugging...",
          "⚠️ Fix didn't work...",
          "🔍 Need more investigation...",
          "❌ Issue persists..."
        ]
      },
      'test': {
        success: [
          "🧪 All tests passed!",
          "✅ Green across the board!",
          "🎯 100% success rate!",
          "⚡ Tests complete!",
          "🔥 Everything works!"
        ],
        failure: [
          "⚠️ Some tests failed...",
          "❌ Found issues in testing...",
          "🔧 Tests reveal bugs...",
          "🚫 Test suite failed..."
        ]
      },
      'default': {
        success: [
          "✅ Done!",
          "🎯 Success!",
          "⚡ Complete!",
          "🔥 Finished!"
        ],
        failure: [
          "⚠️ Issue detected...",
          "❌ Failed...",
          "🔧 Need to fix this...",
          "🚫 Couldn't complete..."
        ]
      }
    };
  }

  getPersonalityHook(action: string, success: boolean): string {
    const actionHooks = this.hooks[action] || this.hooks.default;
    const hooksList = success ? actionHooks.success : actionHooks.failure;
    
    const randomIndex = Math.floor(Math.random() * hooksList.length);
    return hooksList[randomIndex];
  }

  getContextNote(action: string, userInput: string): string {
    const hour = new Date().getHours();

    // Time-based context
    if (hour >= 20 && hour < 24) {
      return "🌙 Working late in Rabat! Here's what I did:";
    } else if (hour >= 0 && hour < 6) {
      return "🌃 Burning the midnight oil! Check this out:";
    } else if (hour >= 6 && hour < 9) {
      return "☀️ Early bird catches the code! Here we go:";
    } else if (hour >= 12 && hour < 14) {
      return "🍽️ Lunch break coding? Nice! Here's what I built:";
    }

    // Pattern-based context (if memory available)
    if (this.memory && typeof this.memory.search === 'function') {
      // @ts-ignore - memory interface not fully defined
      const similarCount = this.memory.search(action).length;
      if (similarCount >= 3) {
        return `💡 Based on your last ${similarCount} similar tasks...`;
      }
    }

    return "";
  }

  suggestNextSteps(action: string, success: boolean): SmartSuggestions[] {
    if (!success) {
      // On failure, suggest debugging/fixing
      return [
        { label: "🔍 Debug", callback: `debug_${action}` },
        { label: "📋 View Logs", callback: "action_logs" },
        { label: "❓ Get Help", callback: "action_help" },
        { label: "🔄 Retry", callback: `retry_${action}` },
      ];
    }

    // Success suggestions by action type
    const suggestions: { [action: string]: SmartSuggestions[] } = {
      'build': [
        { label: "🧪 Test", callback: "action_test" },
        { label: "🚀 Deploy", callback: "action_deploy" },
        { label: "💻 View Code", callback: "action_code" },
        { label: "📝 Add Feature", callback: "action_build" },
      ],
      'deploy': [
        { label: "📊 Monitor", callback: "action_monitor" },
        { label: "📱 Announce", callback: "action_post" },
        { label: "📈 Analytics", callback: "action_analytics" },
        { label: "🔒 Audit", callback: "action_audit" },
      ],
      'post': [
        { label: "📊 Check Stats", callback: "action_social_analytics" },
        { label: "🔥 Post Again", callback: "action_post" },
        { label: "📅 Schedule Next", callback: "action_schedule" },
        { label: "🎯 Optimize", callback: "action_viral" },
      ],
      'test': [
        { label: "🚀 Deploy", callback: "action_deploy" },
        { label: "📊 Coverage", callback: "action_test_coverage" },
        { label: "🔧 Fix Issues", callback: "action_fix" },
        { label: "📝 Add Tests", callback: "action_test_add" },
      ],
      'fix': [
        { label: "🧪 Test Fix", callback: "action_test" },
        { label: "🚀 Deploy", callback: "action_deploy" },
        { label: "📝 Document", callback: "action_docs" },
        { label: "✅ Mark Done", callback: "action_mark_done" },
      ]
    };

    return suggestions[action] || [
      { label: "🏠 Main Menu", callback: "menu_main" },
      { label: "📊 Status", callback: "action_status" },
      { label: "❓ Help", callback: "action_help" },
    ].slice(0, 4); // Max 4 suggestions
  }

  buildResponse(
    action: string,
    success: boolean,
    resultText: string,
    userInput: string = "",
    includeSuggestions: boolean = true
  ): { responseText: string; keyboard?: ReturnType<typeof Markup.inlineKeyboard> } {
    // 1. Personality hook
    const hook = this.getPersonalityHook(action, success);

    // 2. Context note
    const contextNote = this.getContextNote(action, userInput);

    // 3. Build response text
    const parts: string[] = [hook];

    if (contextNote) {
      parts.push(`\n${contextNote}`);
    }

    parts.push(`\n${resultText}`);

    const responseText = parts.join('');

    // 4. Suggestions
    let keyboard: ReturnType<typeof Markup.inlineKeyboard> | undefined;
    if (includeSuggestions) {
      const suggestions = this.suggestNextSteps(action, success);

      if (suggestions.length > 0) {
        const fullResponseText = `${responseText}\n\n**Next steps:**`;
        
        // Build keyboard
        const buttonRows = suggestions.map(s => [Markup.button.callback(s.label, s.callback)]);
        buttonRows.push([Markup.button.callback("🏠 Main Menu", "menu_main")]);

        keyboard = Markup.inlineKeyboard(buttonRows);
      }
    }

    return { responseText, keyboard };
  }
}

// Example usage and testing
/*
import { SmartResponse } from '../src/smart_response';

console.log('Testing SmartResponse...');

const sr = new SmartResponse();

// Test 1: Successful build
console.log('\n=== Test 1: Successful Build ===');
const { responseText, keyboard } = sr.buildResponse(
  'build',
  true,
  "Built React app in 12.3s\n• TypeScript ✅\n• Tailwind CSS ✅\n• 47 files created",
  "Build a React app"
);
console.log(responseText);
console.log(`Keyboard: ${keyboard !== undefined}`);

// Test 2: Failed deployment
console.log('\n=== Test 2: Failed Deployment ===');
const result2 = sr.buildResponse(
  'deploy',
  false,
  "Deployment failed:\n• Error: Port 443 already in use\n• Check if another service is running",
  "Deploy to production"
);
console.log(result2.responseText);

// Test 3: Successful post
console.log('\n=== Test 3: Successful Post ===');
const result3 = sr.buildResponse(
  'post',
  true,
  "Posted to:\n• Twitter/X ✅\n• LinkedIn ✅\n\nReach: ~2.4K followers",
  "Post about my new project"
);
console.log(result3.responseText);

console.log('\n✅ SmartResponse tests complete!');
*/