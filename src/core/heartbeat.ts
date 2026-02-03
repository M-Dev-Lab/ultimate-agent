import * as schedule from 'node-schedule';
import * as path from 'path';
import { MemoryManager } from '../memory/memory_manager.js';

interface HeartbeatConfig {
  intervalMinutes: number;
  enabled: boolean;
}

interface HeartbeatResult {
  status: 'OK' | 'ALERT';
  message: string;
  actionTaken?: string;
}

export class HeartbeatEngine {
  private memory: MemoryManager;
  private bot: any;
  private config: HeartbeatConfig;
  private job: schedule.Job | null = null;

  constructor(memory: MemoryManager, bot: any, config?: Partial<HeartbeatConfig>) {
    this.memory = memory;
    this.bot = bot;
    this.config = {
      intervalMinutes: 30,
      enabled: true,
      ...config
    };
    this.job = null;
  }

  start(): void {
    if (!this.config.enabled) {
      console.log('💓 Heartbeat is disabled');
      return;
    }

    console.log(`💓 Starting heartbeat: every ${this.config.intervalMinutes} minutes`);
    
    this.job = schedule.scheduleJob(
      `*/${this.config.intervalMinutes} * * * *`,
      () => this.runHeartbeat()
    );
    
    console.log('✅ Heartbeat scheduled successfully');
  }

  stop(): void {
    if (this.job) {
      schedule.cancelJob(this.job);
      this.job = null;
      console.log('✅ Heartbeat stopped');
    }
  }

  private async runHeartbeat(): Promise<void> {
    console.log(`💓 Heartbeat check: ${new Date().toISOString()}`);
    
    try {
      const context = await this.memory.getContext(1);
      
      const heartbeatPath = path.join(process.cwd(), 'memory', 'HEARTBEAT.md');
      let checklist = '';
      
      try {
        checklist = await this.readMemoryFile(heartbeatPath);
      } catch (error) {
        console.warn('Could not read heartbeat checklist:', error);
        checklist = '# No heartbeat checklist configured';
      }
      
      const prompt = `You are running a proactive heartbeat check.

## Your Identity
${context.soul || 'Loading soul...'}

## User Context  
${context.identity || 'Loading identity...'}

## Heartbeat Checklist
${checklist}

## Instructions
1. Check each item in the checklist
2. If NOTHING needs attention, reply exactly: "HEARTBEAT_OK"
3. If something needs attention, be concise:
   - State what needs attention
   - Suggest action if appropriate
   - Keep it under 100 words

## Recent Activity (Last 24h)
${context.recentLogs && context.recentLogs[0] ? context.recentLogs[0].content.substring(0, 500) : 'No recent activity'}

Now run the heartbeat check and return ONLY the result (either "HEARTBEAT_OK" or a brief alert message):`;

      const response = await this.callModel(prompt);
      
      if (response.trim() !== 'HEARTBEAT_OK') {
        console.log(`🚨 Heartbeat Alert: ${response}`);
        await this.sendAlert(response);
      } else {
        console.log('✅ Heartbeat OK - no action needed');
      }
      
    } catch (error) {
      console.error('❌ Heartbeat error:', error);
    }
  }

  private async readMemoryFile(filePath: string): Promise<string> {
    try {
      const fs = await import('fs');
      return await fs.promises.readFile(filePath, 'utf-8');
    } catch (error) {
      return `Error reading file: ${(error as Error).message}`;
    }
  }

  private async callModel(prompt: string): Promise<string> {
    const { OllamaQwenTool } = await import('../tools/ollamaQwenTool.js');
    const qwenTool = new OllamaQwenTool();
    
    try {
      const response = await qwenTool.chatWithOllama(prompt);
      return response || 'Model unavailable';
    } catch (error) {
      console.error('Model error:', error);
      return `Heartbeat error: ${(error as Error).message}`;
    }
  }

  private async sendAlert(message: string): Promise<void> {
    try {
      if (this.bot && this.bot.sendMessage) {
        await this.bot.sendMessage({
          channel: 'telegram',
          content: `💓 Heartbeat Alert\n\n${message}`
        });
      }
    } catch (error) {
      console.error('Failed to send alert:', error);
    }
  }

  setInterval(minutes: number): void {
    this.config.intervalMinutes = minutes;
    if (this.job) {
      this.stop();
      this.start();
    }
  }

  enable(): void {
    this.config.enabled = true;
    if (!this.job) {
      this.start();
    }
  }

  disable(): void {
    this.config.enabled = false;
    if (this.job) {
      this.stop();
    }
  }

  getConfig(): HeartbeatConfig {
    return { ...this.config };
  }
}