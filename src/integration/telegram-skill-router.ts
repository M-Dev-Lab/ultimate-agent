/**
 * Telegram Skill Router
 * 
 * Maps Telegram commands and messages to agent skills with:
 * - Context extraction
 * - Skill selection strategy
 * - Command parsing
 * - Chaining logic
 * - Response formatting
 */

import { Context } from 'telegraf';
import { EventEmitter } from 'events';

interface CommandMetadata {
  command: string;
  args: string[];
  rawInput: string;
  isButton: boolean;
  buttonAction?: string;
}

interface SkillRoute {
  skillId: string;
  confidence: number;
  chain?: string[]; // Skills to chain after main skill
  parameters?: Record<string, any>;
  timeoutMs: number;
}

/**
 * Maps Telegram commands to skills
 */
const COMMAND_SKILL_MAP: Record<string, string> = {
  '/build': 'skill_code',
  '/code': 'skill_code',
  '/write': 'skill_code',
  '/generate': 'skill_code',

  '/test': 'skill_test',
  '/debug': 'skill_debug',
  '/analyze': 'skill_analyze',
  '/learn': 'skill_learn',

  '/fix': 'skill_debug',
  '/help': 'skill_analyze',

  '/post': 'skill_code', // Social media posting
  '/deploy': 'skill_code', // Deployment
  '/audit': 'skill_analyze', // Security audit
};

/**
 * Maps button actions to skills and chains
 */
const BUTTON_ACTION_SKILL_MAP: Record<string, SkillRoute> = {
  'cmd_build': {
    skillId: 'skill_code',
    confidence: 0.95,
    chain: ['skill_test', 'skill_analyze'],
    timeoutMs: 30000,
  },
  'cmd_code': {
    skillId: 'skill_code',
    confidence: 0.9,
    timeoutMs: 20000,
  },
  'cmd_fix': {
    skillId: 'skill_debug',
    confidence: 0.85,
    chain: ['skill_test'],
    timeoutMs: 25000,
  },
  'cmd_test': {
    skillId: 'skill_test',
    confidence: 0.9,
    timeoutMs: 25000,
  },
  'cmd_analyze': {
    skillId: 'skill_analyze',
    confidence: 0.85,
    timeoutMs: 20000,
  },
  'cmd_learn': {
    skillId: 'skill_learn',
    confidence: 0.8,
    timeoutMs: 15000,
  },
  'cmd_post': {
    skillId: 'skill_code',
    confidence: 0.8,
    parameters: { type: 'social_media' },
    timeoutMs: 20000,
  },
  'cmd_deploy': {
    skillId: 'skill_code',
    confidence: 0.85,
    parameters: { type: 'deployment' },
    timeoutMs: 30000,
  },
  'cmd_audit': {
    skillId: 'skill_analyze',
    confidence: 0.8,
    parameters: { type: 'security' },
    timeoutMs: 20000,
  },
  'cmd_debug': {
    skillId: 'skill_debug',
    confidence: 0.85,
    timeoutMs: 25000,
  },
};

/**
 * Keywords that trigger specific skills (for free-text routing)
 */
const KEYWORD_SKILL_MAP: Record<string, { skill: string; weight: number }> = {
  // Code/Build keywords
  'create': { skill: 'skill_code', weight: 0.8 },
  'write': { skill: 'skill_code', weight: 0.9 },
  'generate': { skill: 'skill_code', weight: 0.85 },
  'build': { skill: 'skill_code', weight: 0.9 },
  'implement': { skill: 'skill_code', weight: 0.85 },
  'function': { skill: 'skill_code', weight: 0.7 },
  'class': { skill: 'skill_code', weight: 0.7 },
  'api': { skill: 'skill_code', weight: 0.8 },
  'endpoint': { skill: 'skill_code', weight: 0.7 },

  // Test keywords
  'test': { skill: 'skill_test', weight: 0.95 },
  'unit': { skill: 'skill_test', weight: 0.9 },
  'integration': { skill: 'skill_test', weight: 0.9 },
  'e2e': { skill: 'skill_test', weight: 0.85 },
  'mock': { skill: 'skill_test', weight: 0.8 },
  'assertion': { skill: 'skill_test', weight: 0.85 },

  // Debug keywords
  'fix': { skill: 'skill_debug', weight: 0.95 },
  'debug': { skill: 'skill_debug', weight: 0.95 },
  'error': { skill: 'skill_debug', weight: 0.9 },
  'bug': { skill: 'skill_debug', weight: 0.95 },
  'issue': { skill: 'skill_debug', weight: 0.85 },
  'crash': { skill: 'skill_debug', weight: 0.9 },
  'exception': { skill: 'skill_debug', weight: 0.85 },

  // Analyze keywords
  'analyze': { skill: 'skill_analyze', weight: 0.9 },
  'review': { skill: 'skill_analyze', weight: 0.85 },
  'evaluate': { skill: 'skill_analyze', weight: 0.8 },
  'audit': { skill: 'skill_analyze', weight: 0.85 },
  'optimize': { skill: 'skill_analyze', weight: 0.8 },
  'refactor': { skill: 'skill_analyze', weight: 0.85 },
  'performance': { skill: 'skill_analyze', weight: 0.8 },

  // Learn keywords
  'explain': { skill: 'skill_learn', weight: 0.85 },
  'how': { skill: 'skill_learn', weight: 0.8 },
  'teach': { skill: 'skill_learn', weight: 0.85 },
  'learn': { skill: 'skill_learn', weight: 0.9 },
  'tutorial': { skill: 'skill_learn', weight: 0.85 },
  'documentation': { skill: 'skill_learn', weight: 0.8 },
};

export class TelegramSkillRouter extends EventEmitter {
  private commandHistory: Map<number, string[]> = new Map(); // userId -> recent commands
  private maxHistorySize: number = 50;

  /**
   * Extract command metadata from message
   */
  extractCommand(ctx: Context, message: string): CommandMetadata | null {
    // Check if it's a button action
    if (ctx.callbackQuery) {
      const buttonAction = (ctx.callbackQuery as any).data;
      return {
        command: buttonAction,
        args: [],
        rawInput: message,
        isButton: true,
        buttonAction,
      };
    }

    // Parse text command
    const commandMatch = message.match(/^\/(\w+)\s*(.*)/);
    if (commandMatch) {
      const [, cmd, argsStr] = commandMatch;
      const args = argsStr.split(/\s+/).filter(a => a.length > 0);

      return {
        command: `/${cmd}`,
        args,
        rawInput: message,
        isButton: false,
      };
    }

    // No explicit command
    return null;
  }

  /**
   * Route message to appropriate skill(s)
   */
  routeMessage(userId: number, message: string, ctx: Context): SkillRoute {
    // Update command history
    this.updateCommandHistory(userId, message);

    // Check for button action first
    if (ctx.callbackQuery) {
      const buttonAction = (ctx.callbackQuery as any).data;
      const route = BUTTON_ACTION_SKILL_MAP[buttonAction];

      if (route) {
        this.emit('routed', {
          userId,
          type: 'button',
          route,
          message,
        });
        return route;
      }
    }

    // Check for explicit command
    const commandMatch = message.match(/^\/(\w+)/);
    if (commandMatch) {
      const command = `/${commandMatch[1]}`;
      const skillId = COMMAND_SKILL_MAP[command];

      if (skillId) {
        const route: SkillRoute = {
          skillId,
          confidence: 0.9,
          timeoutMs: 20000,
        };

        this.emit('routed', {
          userId,
          type: 'command',
          command,
          route,
        });

        return route;
      }
    }

    // Route by keyword analysis for free text
    return this.routeByKeywords(userId, message);
  }

  /**
   * Route by analyzing keywords in message
   */
  private routeByKeywords(userId: number, message: string): SkillRoute {
    const lowerMessage = message.toLowerCase();
    const words = lowerMessage.split(/\s+/);

    const skillScores: Record<string, number> = {};

    // Score each keyword
    for (const word of words) {
      const wordClean = word.replace(/[^\w]/g, '');
      const keywordEntry = KEYWORD_SKILL_MAP[wordClean];

      if (keywordEntry) {
        const { skill, weight } = keywordEntry;
        skillScores[skill] = (skillScores[skill] || 0) + weight;
      }
    }

    // Find best skill
    let bestSkill = 'skill_code'; // Default
    let bestScore = 0;

    for (const [skill, score] of Object.entries(skillScores)) {
      if (score > bestScore) {
        bestScore = score;
        bestSkill = skill;
      }
    }

    // Calculate confidence based on score
    const confidence = Math.min(0.95, 0.5 + bestScore / 10);

    const route: SkillRoute = {
      skillId: bestSkill,
      confidence: Math.round(confidence * 100) / 100,
      timeoutMs: 20000,
    };

    // Add chaining logic based on context
    if (bestSkill === 'skill_code') {
      // If message mentions testing, add test skill to chain
      if (lowerMessage.includes('test') || lowerMessage.includes('validate')) {
        route.chain = ['skill_test'];
      }
    } else if (bestSkill === 'skill_debug') {
      // If debugging, chain with test to verify fix
      if (lowerMessage.includes('verify') || lowerMessage.includes('check')) {
        route.chain = ['skill_test'];
      }
    }

    this.emit('routed', {
      userId,
      type: 'freetext',
      route,
      bestSkill,
      confidence,
      keywordScore: bestScore,
    });

    return route;
  }

  /**
   * Get suggested skill for message preview
   */
  getSuggestedSkill(message: string): {
    skill: string;
    displayName: string;
    emoji: string;
  } {
    const lowerMessage = message.toLowerCase();

    // Quick check for dominant keywords
    if (lowerMessage.includes('test')) {
      return { skill: 'skill_test', displayName: '🧪 Testing', emoji: '🧪' };
    }
    if (lowerMessage.includes('fix') || lowerMessage.includes('bug') || lowerMessage.includes('debug')) {
      return { skill: 'skill_debug', displayName: '🔧 Debugging', emoji: '🔧' };
    }
    if (lowerMessage.includes('analyze') || lowerMessage.includes('review') || lowerMessage.includes('optimize')) {
      return { skill: 'skill_analyze', displayName: '📊 Analysis', emoji: '📊' };
    }
    if (lowerMessage.includes('explain') || lowerMessage.includes('learn') || lowerMessage.includes('how')) {
      return { skill: 'skill_learn', displayName: '🧠 Learning', emoji: '🧠' };
    }

    // Default to code
    return { skill: 'skill_code', displayName: '💻 Coding', emoji: '💻' };
  }

  /**
   * Build message context for agent
   */
  buildSkillContext(
    message: string,
    route: SkillRoute,
    ctx: Context
  ): Record<string, any> {
    const from = ctx.from;
    const msg = ctx.message;

    return {
      skill: route.skillId,
      chain: route.chain,
      confidence: route.confidence,
      userMessage: message,
      userId: from?.id,
      username: from?.username,
      messageId: msg?.message_id,
      isReply: msg?.reply_to_message ? true : false,
      replyToUser: msg?.reply_to_message?.from?.username,
      parameters: route.parameters || {},
      timeout: route.timeoutMs,
      timestamp: (msg?.date || 0) * 1000,
    };
  }

  /**
   * Update command history for user
   */
  private updateCommandHistory(userId: number, command: string): void {
    if (!this.commandHistory.has(userId)) {
      this.commandHistory.set(userId, []);
    }

    const history = this.commandHistory.get(userId)!;
    history.push(command);

    // Keep only recent history
    if (history.length > this.maxHistorySize) {
      history.shift();
    }
  }

  /**
   * Get command history for user
   */
  getCommandHistory(userId: number): string[] {
    return this.commandHistory.get(userId) || [];
  }

  /**
   * Clear history for user
   */
  clearHistory(userId: number): void {
    this.commandHistory.delete(userId);
  }

  /**
   * Get routing statistics
   */
  getStats(): {
    totalUsersTracked: number;
    totalCommandsTracked: number;
    skillDistribution: Record<string, number>;
  } {
    let totalCommands = 0;
    const skillDist: Record<string, number> = {};

    for (const history of this.commandHistory.values()) {
      totalCommands += history.length;
    }

    return {
      totalUsersTracked: this.commandHistory.size,
      totalCommandsTracked: totalCommands,
      skillDistribution: skillDist,
    };
  }

  /**
   * Get help message for all commands
   */
  getCommandHelp(): string {
    return `📖 *Available Commands*

*Coding:*
/build - Create a new project
/code - Generate code
/write - Write code/documentation
/generate - Generate code

*Testing & Debugging:*
/test - Write tests
/debug - Debug code
/fix - Fix errors/bugs

*Analysis:*
/analyze - Analyze code
/learn - Learn & explain concepts

*Or just type naturally!*
"Write a REST API" or "Fix this error"`;
  }
}

/**
 * Create singleton router instance
 */
let routerInstance: TelegramSkillRouter | null = null;

export function initializeSkillRouter(): TelegramSkillRouter {
  if (!routerInstance) {
    routerInstance = new TelegramSkillRouter();
  }
  return routerInstance;
}

export function getSkillRouter(): TelegramSkillRouter | null {
  return routerInstance;
}

export function resetSkillRouter(): void {
  routerInstance = null;
}
