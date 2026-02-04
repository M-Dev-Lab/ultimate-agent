/**
 * Intelligent Skill System
 * Manages skill registration, routing, and execution
 * 
 * Features:
 * - Dynamic skill registration
 * - Context-aware routing
 * - Skill chaining
 * - Error recovery
 * - Performance metrics
 */

import { EventEmitter } from 'events';
import { OllamaClient, ChatMessage } from './ollama_integration.js';
import * as fs from 'fs/promises';
import * as path from 'path';

// ============= TYPES =============

export type SkillPriority = 'critical' | 'high' | 'normal' | 'low';
export type SkillCategory = 
  | 'coding'
  | 'analysis'
  | 'browser'
  | 'social'
  | 'memory'
  | 'learning'
  | 'utility'
  | 'system';

export interface SkillDefinition {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  priority: SkillPriority;
  enabled: boolean;
  version: string;
  dependencies?: string[];
  maxDuration?: number;
  retryable?: boolean;
  metadata?: Record<string, any>;
}

export interface SkillInput {
  context: string;
  parameters: Record<string, any>;
  userId?: string;
  sessionId?: string;
  conversationHistory?: ChatMessage[];
}

export interface SkillOutput {
  skillId: string;
  success: boolean;
  result?: any;
  error?: string;
  metrics: {
    duration: number;
    tokensUsed?: number;
    cacheHit?: boolean;
  };
  chained?: string[]; // IDs of skills that can be chained after this
}

export interface SkillExecutor {
  (input: SkillInput, client: OllamaClient): Promise<SkillOutput>;
}

// ============= SKILL MANAGER =============

export class SkillSystem extends EventEmitter {
  private skills: Map<string, {
    definition: SkillDefinition;
    executor: SkillExecutor;
  }> = new Map();

  private executionHistory: Array<{
    skillId: string;
    timestamp: number;
    duration: number;
    success: boolean;
    error?: string;
  }> = [];

  private ollamaClient: OllamaClient;
  private skillWeights: Map<string, number> = new Map();

  constructor(ollamaClient: OllamaClient) {
    super();
    this.ollamaClient = ollamaClient;
    this.initializeBuiltInSkills();
  }

  // ============= SKILL REGISTRATION =============

  /**
   * Register a new skill
   */
  registerSkill(
    definition: SkillDefinition,
    executor: SkillExecutor
  ): void {
    if (this.skills.has(definition.id)) {
      console.warn(`⚠️  Skill ${definition.id} already registered, overwriting`);
    }

    this.skills.set(definition.id, { definition, executor });
    this.skillWeights.set(definition.id, this.calculateInitialWeight(definition));

    console.log(`✓ Registered skill: ${definition.name} (${definition.category})`);
    this.emit('skillRegistered', definition);
  }

  /**
   * Unregister a skill
   */
  unregisterSkill(skillId: string): boolean {
    const removed = this.skills.delete(skillId);
    if (removed) {
      this.skillWeights.delete(skillId);
      console.log(`✓ Unregistered skill: ${skillId}`);
      this.emit('skillUnregistered', skillId);
    }
    return removed;
  }

  /**
   * Enable/disable a skill
   */
  setSkillEnabled(skillId: string, enabled: boolean): boolean {
    const skill = this.skills.get(skillId);
    if (!skill) return false;

    skill.definition.enabled = enabled;
    console.log(`${enabled ? '✓' : '✗'} Skill ${skillId} ${enabled ? 'enabled' : 'disabled'}`);
    return true;
  }

  // ============= SKILL EXECUTION =============

  /**
   * Execute a single skill
   */
  async executeSkill(
    skillId: string,
    input: SkillInput
  ): Promise<SkillOutput> {
    const skill = this.skills.get(skillId);
    if (!skill) {
      throw new Error(`Skill not found: ${skillId}`);
    }

    if (!skill.definition.enabled) {
      throw new Error(`Skill disabled: ${skillId}`);
    }

    const startTime = Date.now();
    console.log(`⚙️  Executing skill: ${skill.definition.name}`);

    try {
      // Check dependencies
      if (skill.definition.dependencies?.length) {
        await this.resolveDependencies(skill.definition.dependencies);
      }

      // Execute with timeout
      const result = await this.executeWithTimeout(
        skill.executor,
        input,
        skill.definition.maxDuration || 30000
      );

      const duration = Date.now() - startTime;

      // Log execution
      this.executionHistory.push({
        skillId,
        timestamp: Date.now(),
        duration,
        success: true
      });

      // Update weights based on success
      this.updateSkillWeight(skillId, true, duration);

      console.log(`✓ Skill completed in ${duration}ms`);
      this.emit('skillExecuted', { skillId, duration, success: true });

      return { ...result, skillId, metrics: { duration } };
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMsg = error instanceof Error ? error.message : String(error);

      // Log failure
      this.executionHistory.push({
        skillId,
        timestamp: Date.now(),
        duration,
        success: false,
        error: errorMsg
      });

      // Update weights based on failure
      this.updateSkillWeight(skillId, false, duration);

      console.error(`✗ Skill failed: ${errorMsg}`);
      this.emit('skillFailed', { skillId, duration, error: errorMsg });

      return {
        skillId,
        success: false,
        error: errorMsg,
        metrics: { duration },
        chained: []
      };
    }
  }

  /**
   * Intelligently route to the best skill for a task
   */
  async routeTask(
    taskDescription: string,
    input: SkillInput
  ): Promise<SkillOutput> {
    // Get candidate skills
    const candidates = this.rankSkillsForTask(taskDescription);

    if (candidates.length === 0) {
      return {
        skillId: 'none',
        success: false,
        error: 'No suitable skills found for task',
        metrics: { duration: 0 }
      };
    }

    // Try skills in ranked order
    for (const skillId of candidates) {
      try {
        console.log(`🎯 Routing task to: ${this.skills.get(skillId)?.definition.name}`);
        return await this.executeSkill(skillId, input);
      } catch (error) {
        console.warn(`⚠️  Failed routing to ${skillId}, trying next...`);
        continue;
      }
    }

    return {
      skillId: 'none',
      success: false,
      error: 'All candidate skills failed',
      metrics: { duration: 0 }
    };
  }

  /**
   * Chain multiple skills together
   */
  async chainSkills(
    skillIds: string[],
    initialInput: SkillInput
  ): Promise<SkillOutput[]> {
    const results: SkillOutput[] = [];
    let currentInput = initialInput;

    for (const skillId of skillIds) {
      try {
        const result = await this.executeSkill(skillId, currentInput);
        results.push(result);

        // Pass result as context for next skill
        currentInput = {
          ...currentInput,
          context: result.result || result.error || '',
          parameters: {
            ...currentInput.parameters,
            previousOutput: result
          }
        };

        if (!result.success) {
          console.warn(`Chain interrupted at skill ${skillId}`);
          break;
        }
      } catch (error) {
        console.error(`Error in chain at ${skillId}:`, error);
        break;
      }
    }

    return results;
  }

  // ============= BUILT-IN SKILLS =============

  private initializeBuiltInSkills(): void {
    // Coding skill
    this.registerSkill(
      {
        id: 'skill_code',
        name: 'Code Generation',
        description: 'Generate, analyze, and fix code',
        category: 'coding',
        priority: 'high',
        enabled: true,
        version: '1.0.0'
      },
      async (input) => {
        const response = await this.ollamaClient.chat([
          {
            role: 'system',
            content: 'You are an expert code generator. Produce clean, efficient, well-documented code.'
          },
          {
            role: 'user',
            content: input.context
          }
        ]);

        return {
          success: true,
          result: response.message.content,
          chained: ['skill_test', 'skill_analyze']
        };
      }
    );

    // Analysis skill
    this.registerSkill(
      {
        id: 'skill_analyze',
        name: 'Code Analysis',
        description: 'Analyze code quality, complexity, and potential issues',
        category: 'analysis',
        priority: 'high',
        enabled: true,
        version: '1.0.0'
      },
      async (input) => {
        const response = await this.ollamaClient.chat([
          {
            role: 'system',
            content: 'You are a code review expert. Provide constructive analysis of code quality, performance, and best practices.'
          },
          {
            role: 'user',
            content: `Analyze this code:\n${input.context}`
          }
        ]);

        return {
          success: true,
          result: response.message.content,
          chained: ['skill_learn']
        };
      }
    );

    // Testing skill
    this.registerSkill(
      {
        id: 'skill_test',
        name: 'Test Generation',
        description: 'Generate unit tests and test cases',
        category: 'coding',
        priority: 'normal',
        enabled: true,
        version: '1.0.0'
      },
      async (input) => {
        const response = await this.ollamaClient.chat([
          {
            role: 'system',
            content: 'You are a test automation expert. Generate comprehensive test cases and unit tests.'
          },
          {
            role: 'user',
            content: `Generate tests for:\n${input.context}`
          }
        ]);

        return {
          success: true,
          result: response.message.content,
          chained: []
        };
      }
    );

    // Learning skill
    this.registerSkill(
      {
        id: 'skill_learn',
        name: 'Learning & Documentation',
        description: 'Generate tutorials, explanations, and documentation',
        category: 'learning',
        priority: 'normal',
        enabled: true,
        version: '1.0.0'
      },
      async (input) => {
        const response = await this.ollamaClient.chat([
          {
            role: 'system',
            content: 'You are an expert educator. Provide clear, detailed explanations and learning materials.'
          },
          {
            role: 'user',
            content: `Explain:\n${input.context}`
          }
        ]);

        return {
          success: true,
          result: response.message.content,
          chained: []
        };
      }
    );

    // Debugging skill
    this.registerSkill(
      {
        id: 'skill_debug',
        name: 'Debugging',
        description: 'Debug code and fix issues',
        category: 'coding',
        priority: 'high',
        enabled: true,
        version: '1.0.0'
      },
      async (input) => {
        const response = await this.ollamaClient.chat([
          {
            role: 'system',
            content: 'You are a debugging expert. Identify and fix code issues with detailed explanations.'
          },
          {
            role: 'user',
            content: `Debug this:\n${input.context}`
          }
        ]);

        return {
          success: true,
          result: response.message.content,
          chained: ['skill_test']
        };
      }
    );

    console.log('✓ Built-in skills initialized');
  }

  // ============= PRIVATE HELPERS =============

  /**
   * Rank skills by relevance to task
   */
  private rankSkillsForTask(task: string): string[] {
    const keywords: Record<string, string[]> = {
      skill_code: ['code', 'write', 'implement', 'generate', 'function', 'class', 'method'],
      skill_analyze: ['analyze', 'review', 'check', 'quality', 'complexity'],
      skill_test: ['test', 'unit test', 'integration', 'coverage'],
      skill_debug: ['debug', 'fix', 'error', 'bug', 'issue', 'problem'],
      skill_learn: ['explain', 'understand', 'learn', 'tutorial', 'documentation']
    };

    const scores = new Map<string, number>();

    // Score each skill
    for (const [skillId, keywords] of Object.entries(keywords)) {
      let score = 0;
      for (const keyword of keywords) {
        if (task.toLowerCase().includes(keyword)) {
          score++;
        }
      }
      scores.set(skillId, score + (this.skillWeights.get(skillId) || 0));
    }

    // Sort by score descending
    return Array.from(scores.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([skillId]) => skillId)
      .filter(skillId => {
        const skill = this.skills.get(skillId);
        return skill?.definition.enabled;
      });
  }

  /**
   * Resolve skill dependencies
   */
  private async resolveDependencies(dependencies: string[]): Promise<void> {
    for (const depId of dependencies) {
      if (!this.skills.has(depId)) {
        throw new Error(`Dependency skill not found: ${depId}`);
      }
    }
  }

  /**
   * Execute with timeout
   */
  private executeWithTimeout(
    executor: SkillExecutor,
    input: SkillInput,
    timeout: number
  ): Promise<Omit<SkillOutput, 'skillId'>> {
    return Promise.race([
      executor(input, this.ollamaClient),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Skill execution timeout after ${timeout}ms`)), timeout)
      )
    ]);
  }

  /**
   * Calculate initial skill weight
   */
  private calculateInitialWeight(definition: SkillDefinition): number {
    const priorityWeights: Record<SkillPriority, number> = {
      critical: 10,
      high: 7,
      normal: 5,
      low: 2
    };
    return priorityWeights[definition.priority];
  }

  /**
   * Update skill weight based on success/failure
   */
  private updateSkillWeight(skillId: string, success: boolean, duration: number): void {
    const current = this.skillWeights.get(skillId) || 5;
    const adjustment = success
      ? 0.1 * (1000 / duration) // Faster executions boost weight
      : -0.2; // Failures reduce weight

    const newWeight = Math.max(0.5, Math.min(10, current + adjustment));
    this.skillWeights.set(skillId, newWeight);
  }

  // ============= PUBLIC ANALYTICS =============

  /**
   * Get all registered skills
   */
  getSkills(): SkillDefinition[] {
    return Array.from(this.skills.values()).map(s => s.definition);
  }

  /**
   * Get skill stats
   */
  getSkillStats(skillId?: string) {
    const filtered = skillId
      ? this.executionHistory.filter(h => h.skillId === skillId)
      : this.executionHistory;

    const successful = filtered.filter(h => h.success).length;
    const avgDuration = filtered.length > 0
      ? filtered.reduce((sum, h) => sum + h.duration, 0) / filtered.length
      : 0;

    return {
      totalExecutions: filtered.length,
      successful,
      failed: filtered.length - successful,
      successRate: filtered.length > 0 ? (successful / filtered.length) * 100 : 0,
      avgDuration: Math.round(avgDuration),
      skillCount: this.skills.size
    };
  }

  /**
   * Reset skill system
   */
  async reset(): Promise<void> {
    this.executionHistory = [];
    this.skillWeights.clear();
    this.skills.forEach(skill => {
      this.skillWeights.set(skill.definition.id, this.calculateInitialWeight(skill.definition));
    });
    console.log('✓ Skill system reset');
  }
}

export default SkillSystem;
