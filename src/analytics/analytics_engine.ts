import { promises as fs } from 'fs';
import { open } from 'sqlite';

export interface CommandStats {
  command: string;
  count: number;
  successRate: number;
  avgExecutionTime: number;
  lastUsed: Date;
}

export interface ModelStats {
  model: string;
  uses: number;
  successRate: number;
  avgExecutionTime: number;
  costTotal: number;
}

export interface UserBehavior {
  commonCommands: string[];
  preferredTime: string[];
  commandFrequency: Map<string, number>;
  interactionPatterns: string[];
}

export interface ImprovementSuggestion {
  category: 'commands' | 'prompts' | 'skills' | 'models' | 'workflow';
  suggestion: string;
  priority: 'low' | 'medium' | 'high';
  reason: string;
}

export class AnalyticsEngine {
  private dbPath: string;
  private commandStats: Map<string, CommandStats>;
  private modelStats: Map<string, ModelStats>;
  private userBehavior: UserBehavior;
  private improvementSuggestions: ImprovementSuggestion[] = [];
  private enabled: boolean = true;

  constructor(dbPath: string = './data/db/interactions.db') {
    this.dbPath = dbPath;
    this.commandStats = new Map();
    this.modelStats = new Map();
    this.userBehavior = {
      commonCommands: [],
      preferredTime: [],
      commandFrequency: new Map(),
      interactionPatterns: []
    };
  }

  async initialize(): Promise<void> {
    try {
      console.log('📊 Initializing Analytics Engine...');
      await this.loadStatsFromDatabase();
      await this.analyzeUserBehavior();
      await this.generateImprovements();
      console.log('✅ Analytics Engine initialized');
    } catch (error) {
      console.error('❌ Failed to initialize Analytics Engine:', error);
    }
  }

  private async loadStatsFromDatabase(): Promise<void> {
    try {
      const db = await open({
        filename: this.dbPath,
        driver: require('sqlite3').Database
      });

      const results = await db.all(`
        SELECT 
          command,
          model_used,
          success,
          execution_time,
          timestamp
        FROM interactions
        ORDER BY timestamp DESC
        LIMIT 1000
      `);

      this.processInteractionResults(results);

      await db.close();
    } catch (error) {
      console.error('Failed to load stats from database:', error);
    }
  }

  private processInteractionResults(results: any[]): void {
    this.commandStats.clear();
    this.modelStats.clear();

    for (const row of results) {
      const command = row.command || 'unknown';
      const model = row.model_used || 'unknown';
      const success = row.success ? 1 : 0;
      const executionTime = row.execution_time || 0;

      if (!this.commandStats.has(command)) {
        this.commandStats.set(command, {
          command,
          count: 0,
          successRate: 0,
          avgExecutionTime: 0,
          lastUsed: new Date(row.timestamp)
        });
      }

      const stats = this.commandStats.get(command);
      if (stats) {
        stats.count++;
        stats.successRate = stats.successRate * 0.9 + (success * 0.1);
        stats.avgExecutionTime = ((stats.avgExecutionTime * stats.count) + executionTime) / (stats.count + 1);
        stats.lastUsed = new Date(row.timestamp);
      }

      if (!this.modelStats.has(model)) {
        this.modelStats.set(model, {
          model,
          uses: 0,
          successRate: 0,
          avgExecutionTime: 0,
          costTotal: 0
        });
      }

      const modelStats = this.modelStats.get(model);
      if (modelStats) {
        modelStats.uses++;
        modelStats.successRate = modelStats.successRate * 0.9 + (success * 0.1);
        modelStats.avgExecutionTime = ((modelStats.avgExecutionTime * modelStats.uses) + executionTime) / (modelStats.uses + 1);
      }
    }
  }

  private async analyzeUserBehavior(): Promise<void> {
    const commandArray = Array.from(this.commandStats.values())
      .sort((a, b) => b.count - a.count);

    const topCommands = commandArray.slice(0, 10).map(c => c.command);
    const totalCommands = commandArray.reduce((sum, c) => sum + c.count, 0);

    this.userBehavior.commonCommands = topCommands;

    const topCommandStats = commandArray.slice(0, 10);
    for (const cmd of topCommandStats) {
      this.userBehavior.commandFrequency.set(cmd.command, cmd.count);
    }

    this.userBehavior.interactionPatterns = this.detectPatterns();
  }

  private detectPatterns(): string[] {
    const patterns: string[] = [];

    const stats = Array.from(this.commandStats.values());
    const failureRate = stats.reduce((sum, c) => sum + (c.successRate < 0.5 ? 1 : 0), 0);

    if (failureRate > 0.3) {
      patterns.push('High failure rate detected. Consider reviewing command responses.');
    }

    const avgTime = stats.reduce((sum, c) => sum + c.avgExecutionTime, 0) / stats.length;
    
    if (avgTime > 10) {
      patterns.push('Slow response times. Consider optimizing prompts or using faster models.');
    }

    const mostUsed = stats[0];
    if (mostUsed && mostUsed.count > 50) {
      patterns.push(`Command "${mostUsed.command}" is heavily used. Could add shortcut or button.`);
    }

    return patterns;
  }

  private async generateImprovements(): Promise<void> {
    this.improvementSuggestions = [];

    const commandSuggestions = this.generateCommandImprovements();
    const modelSuggestions = this.generateModelImprovements();
    const skillSuggestions = await this.generateSkillImprovements();
    const workflowSuggestions = this.generateWorkflowImprovements();

    this.improvementSuggestions.push(...commandSuggestions, ...modelSuggestions, ...skillSuggestions, ...workflowSuggestions);
    
    await this.saveImprovements();
  }

  private generateCommandImprovements(): ImprovementSuggestion[] {
    const suggestions: ImprovementSuggestion[] = [];
    const entries = Array.from(this.commandStats.entries());

    for (const [cmd, stats] of entries) {
      if (stats.successRate < 0.7) {
        suggestions.push({
          category: 'commands',
          suggestion: `Command "${cmd}" has low success rate (${(stats.successRate * 100).toFixed(1)}%). Review and improve prompt engineering.`,
          priority: 'high',
          reason: `Success rate below threshold (70%). Last used: ${stats.lastUsed.toISOString()}`
        });
      }

      if (stats.avgExecutionTime > 5) {
        suggestions.push({
          category: 'commands',
          suggestion: `Command "${cmd}" is slow (${stats.avgExecutionTime.toFixed(2)}s avg). Consider optimizing or caching results.`,
          priority: 'medium',
          reason: `Execution time above threshold (5s). Average: ${stats.avgExecutionTime.toFixed(2)}s`
        });
      }
    }

    return suggestions;
  }

  private generateModelImprovements(): ImprovementSuggestion[] {
    const suggestions: ImprovementSuggestion[] = [];
    const entries = Array.from(this.modelStats.entries());

    for (const [model, stats] of entries) {
      if (stats.successRate < 0.8) {
        suggestions.push({
          category: 'models',
          suggestion: `Model "${model}" has reliability issues (${(stats.successRate * 100).toFixed(1)}% success rate). Consider switching to alternative.`,
          priority: 'high',
          reason: `Success rate below threshold (80%). Uses: ${stats.uses}`
        });
      }

      if (stats.avgExecutionTime > 8) {
        suggestions.push({
          category: 'models',
          suggestion: `Model "${model}" is slow (${stats.avgExecutionTime.toFixed(2)}s avg). Try smaller/faster models for simple tasks.`,
          priority: 'medium',
          reason: `Execution time above threshold (8s). Average: ${stats.avgExecutionTime.toFixed(2)}s`
        });
      }
    }

    return suggestions;
  }

  private async generateSkillImprovements(): Promise<ImprovementSuggestion[]> {
    const suggestions: ImprovementSuggestion[] = [];

    try {
      const skillStatsPath = './data/db/skill_usage.json';
      if (await this.fileExists(skillStatsPath)) {
        const skillStats = JSON.parse(await fs.readFile(skillStatsPath, 'utf-8'));

        for (const [skillName, usage] of Object.entries(skillStats)) {
          if (usage && typeof usage === 'object' && 'useCount' in usage) {
            const count = (usage as any).useCount;
            const successRate = (usage as any).successRate || 0;

            if (count < 5 && successRate > 0.9) {
              suggestions.push({
                category: 'skills',
                suggestion: `Skill "${skillName}" is underutilized (${count} uses). Create use cases or documentation.`,
                priority: 'low',
                reason: `Low usage count (threshold: 10). Success rate: ${(successRate * 100).toFixed(1)}%`
              });
            }

            if (successRate < 0.7) {
              suggestions.push({
                category: 'skills',
                suggestion: `Skill "${skillName}" has reliability issues. Review implementation or consider alternatives.`,
                priority: 'high',
                reason: `Success rate below threshold (70%). Uses: ${count}`
              });
            }
          }
        }
      }
    } catch (error) {
      console.warn('Could not analyze skill usage:', error);
    }

    return suggestions;
  }

  private generateWorkflowImprovements(): ImprovementSuggestion[] {
    const suggestions: ImprovementSuggestion[] = [];

    const stats = Array.from(this.commandStats.values());
    const workspaceCommands = stats.filter(s => s.command.startsWith('workspace ') || s.command === 'list');

    if (workspaceCommands.length > 0) {
      const avgWorkspaceTime = workspaceCommands.reduce((sum, c) => sum + c.avgExecutionTime, 0) / workspaceCommands.length;

      if (avgWorkspaceTime > 15) {
        suggestions.push({
          category: 'workflow',
          suggestion: 'Workspace operations are slow. Consider automating common workflows.',
          priority: 'medium',
          reason: `Average workspace time: ${avgWorkspaceTime.toFixed(2)}s (threshold: 15s)`
        });
      }
    }

    const agentCommands = stats.filter(s => s.command.startsWith('agent '));

    if (agentCommands.length > 0) {
      const failures = agentCommands.filter(s => s.successRate < 0.5).length;

      if (failures > agentCommands.length * 0.3) {
        suggestions.push({
          category: 'workflow',
          suggestion: 'High agent failure rate detected. Review agent instructions and task clarity.',
          priority: 'high',
          reason: `${failures}/${agentCommands.length} agent commands failing`
        });
      }
    }

    return suggestions;
  }

  private async saveImprovements(): Promise<void> {
    try {
      const improvementsPath = './data/improvements.json';
      await fs.mkdir('./data', { recursive: true });
      
      const data = {
        lastGenerated: new Date().toISOString(),
        totalSuggestions: this.improvementSuggestions.length,
        suggestions: this.improvementSuggestions,
        commandStats: Array.from(this.commandStats.entries()).map(([key, val]) => ({
          ...val
        })),
        modelStats: Array.from(this.modelStats.entries()).map(([key, val]) => ({
          ...val
        })),
        userBehavior: this.userBehavior
      };

      await fs.writeFile(improvementsPath, JSON.stringify(data, null, 2));
      console.log(`💾 Saved ${this.improvementSuggestions.length} improvement suggestions`);
    } catch (error) {
      console.error('Failed to save improvements:', error);
    }
  }

  async logInteraction(command: string, model: string, success: boolean, executionTime: number): Promise<void> {
    if (!this.enabled) {
      return;
    }

    try {
      const db = await open({
        filename: this.dbPath,
        driver: require('sqlite3').Database
      });

      await db.run(
        `INSERT INTO interactions (command, user_input, success, model_used, execution_time, timestamp)
         VALUES (?, ?, ?, ?, ?, ?)`,
        [command, '', success ? 1 : 0, model, executionTime, new Date().toISOString()]
      );

      await db.close();
      console.log(`📊 Logged interaction: ${command}`);
    } catch (error) {
      console.error('Failed to log interaction:', error);
    }
  }

  getCommandStats(): CommandStats[] {
    return Array.from(this.commandStats.values()).sort((a, b) => b.count - a.count);
  }

  getModelStats(): ModelStats[] {
    return Array.from(this.modelStats.values()).sort((a, b) => b.uses - a.uses);
  }

  getUserBehavior(): UserBehavior {
    return { ...this.userBehavior };
  }

  getImprovements(limit: number = 10): ImprovementSuggestion[] {
    return this.improvementSuggestions.slice(0, limit).sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
  }

  getAnalyticsReport(): {
    summary: string;
    details: any;
  } {
    const commandStats = this.getCommandStats();
    const modelStats = this.getModelStats();

    const totalCommands = commandStats.reduce((sum, c) => sum + c.count, 0);
    const avgSuccessRate = commandStats.reduce((sum, c) => sum + c.successRate, 0) / commandStats.length;

    const topCommands = commandStats.slice(0, 5);
    const topModels = modelStats.slice(0, 3);

    return {
      summary: `📊 Analytics Report\n\nTotal Commands: ${totalCommands}\nAverage Success Rate: ${(avgSuccessRate * 100).toFixed(1)}%\n\nTop Commands:\n${topCommands.map((c, i) => `${i + 1}. ${c.command} (${c.count} uses, ${(c.successRate * 100).toFixed(1)}% success)`).join('\n')}\n\nTop Models:\n${topModels.map((m, i) => `${i + 1}. ${m.model} (${m.uses} uses, ${(m.successRate * 100).toFixed(1)}% success)`).join('\n')}\n\nImprovements: ${this.improvementSuggestions.length} pending suggestions`,
      details: {
        commandStats: this.getCommandStats(),
        modelStats: this.getModelStats(),
        userBehavior: this.getUserBehavior(),
        improvements: this.getImprovements()
      }
    };
  }

  async exportImprovementsToFile(filePath: string): Promise<void> {
    try {
      const data = JSON.stringify(this.getAnalyticsReport(), null, 2);
      await fs.writeFile(filePath, data);
      console.log(`📊 Analytics exported to: ${filePath}`);
    } catch (error) {
      console.error('Failed to export analytics:', error);
    }
  }

  async applyImprovement(suggestionIndex: number): Promise<{ success: boolean; message: string }> {
    if (suggestionIndex < 0 || suggestionIndex >= this.improvementSuggestions.length) {
      return {
        success: false,
        message: 'Invalid improvement index'
      };
    }

    const suggestion = this.improvementSuggestions[suggestionIndex];
    console.log(`🔧 Applying improvement: ${suggestion.suggestion}`);

    return {
      success: true,
      message: `Improvement "${suggestion.category}": ${suggestion.suggestion}`
    };
  }

  enable(): void {
    this.enabled = true;
    console.log('✅ Analytics Engine enabled');
  }

  disable(): void {
    this.enabled = false;
    console.log('✅ Analytics Engine disabled');
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}