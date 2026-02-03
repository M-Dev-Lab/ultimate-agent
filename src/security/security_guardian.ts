import { promises as fs } from 'fs';
import * as path from 'path';

export interface SecurityRule {
  id: string;
  category: 'command' | 'file' | 'network' | 'content' | 'resource';
  severity: 'critical' | 'high' | 'medium' | 'low';
  pattern: RegExp;
  action: 'block' | 'warn' | 'require-confirmation' | 'sanitize';
  description: string;
}

export interface SecurityEvent {
  id: string;
  timestamp: Date;
  event: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  triggeredBy: 'rule' | 'manual';
  input: string;
  action: string;
  blocked: boolean;
  warning: string | null;
}

export interface SecurityConfig {
  enabled: boolean;
  strictMode: boolean;
  allowlist: string[];
  blocklist: string[];
  maxFileSize: number;
  allowedDomains: string[];
  dangerousCommands: string[];
}

export class SecurityGuardian {
  private rules: SecurityRule[];
  private events: SecurityEvent[];
  private config: SecurityConfig;
  private eventsLogPath: string;
  private configPath: string;

  constructor(configPath: string = './security/config.json', eventsLogPath: string = './data/security_events.json') {
    this.configPath = configPath;
    this.eventsLogPath = eventsLogPath;
    this.rules = [];
    this.events = [];
    this.config = this.getDefaultConfig();
    this.loadRules();
    this.loadEvents();
  }

  private getDefaultConfig(): SecurityConfig {
    return {
      enabled: true,
      strictMode: true,
      allowlist: [],
      blocklist: [
        'rm -rf',
        'rm -r',
        'sudo rm',
        'dd',
        'mkfs',
        'format',
        '> /dev/sda',
        '> /dev/sdb',
        'shutdown',
        'poweroff'
      ],
      maxFileSize: 10 * 1024 * 1024,
      allowedDomains: [
        'ollama.com',
        'github.com',
        'cloudflare.com',
        'nodejs.org',
        'npmjs.com'
      ],
      dangerousCommands: [
        'rm',
        'del',
        'format',
        'dd',
        'mkfs'
      ]
    };
  }

  async loadRules(): Promise<void> {
    try {
      if (await this.fileExists(this.configPath)) {
        const content = await fs.readFile(this.configPath, 'utf-8');
        const config = JSON.parse(content);
        this.config = { ...this.getDefaultConfig(), ...config };
        console.log('🔒 Security configuration loaded');
      } else {
        await this.saveConfig();
      }

      this.rules = this.initializeDefaultRules();
    } catch (error) {
      console.error('Failed to load security config:', error);
    }
  }

  private initializeDefaultRules(): SecurityRule[] {
    return [
      {
        id: 'DANGEROUS_DESTRUCTIVE',
        category: 'command',
        severity: 'critical',
        pattern: /^(rm|del|format|dd|mkfs)/i,
        action: 'require-confirmation',
        description: 'Destructive commands require explicit confirmation'
      },
      {
        id: 'FILE_WRITE_PROTECTED',
        category: 'file',
        severity: 'high',
        pattern: /\/(etc|boot|bin|system|root|usr\/bin|usr\/sbin)/i,
        action: 'block',
        description: 'Attempting to write to system directories'
      },
      {
        id: 'EXTERNAL_SCRIPT_EXEC',
        category: 'command',
        severity: 'high',
        pattern: /(\.sh$|\.bash$|\.py$|\.js$)/i,
        action: 'warn',
        description: 'Executing external scripts detected'
      },
      {
        id: 'SUSPICIOUS_URL',
        category: 'network',
        severity: 'high',
        pattern: /(http:\/\/|https:\/\/)[^\s]+(?!(ollama\.com|github\.com|cloudflare\.com|npmjs\.com))/i,
        action: 'block',
        description: 'Accessing suspicious external URLs'
      },
      {
        id: 'LARGE_FILE_SIZE',
        category: 'resource',
        severity: 'medium',
        pattern: /(\s+)\s*(?:b|kb|mb|gb)/i,
        action: 'warn',
        description: 'Large file size in commands'
      },
      {
        id: 'CREDENTIALS_IN_INPUT',
        category: 'content',
        severity: 'critical',
        pattern: /(api[-_]?key|secret|token|password|auth|credential)/i,
        action: 'sanitize',
        description: 'Credentials detected in user input'
      },
      {
        id: 'GIT_FORCE',
        category: 'command',
        severity: 'medium',
        pattern: /(--force|--hard)/i,
        action: 'require-confirmation',
        description: 'Git force operations require confirmation'
      },
      {
        id: 'DOCKER_PRIVILEGED',
        category: 'command',
        severity: 'critical',
        pattern: /(--privileged|--user root|docker.sock)/i,
        action: 'block',
        description: 'Docker privileged operations blocked'
      },
      {
        id: 'SHELL_INJECTION',
        category: 'command',
        severity: 'critical',
        pattern: /[;&|`$|\$\(|\)\s*]/i,
        action: 'block',
        description: 'Shell injection patterns detected'
      }
    ];
  }

  async loadEvents(): Promise<void> {
    try {
      if (await this.fileExists(this.eventsLogPath)) {
        const content = await fs.readFile(this.eventsLogPath, 'utf-8');
        this.events = JSON.parse(content);
      } else {
        this.events = [];
      }
    } catch (error) {
      console.error('Failed to load security events:', error);
      this.events = [];
    }
  }

  async saveConfig(): Promise<void> {
    try {
      await fs.mkdir(path.dirname(this.configPath), { recursive: true });
      await fs.writeFile(this.configPath, JSON.stringify(this.config, null, 2));
    } catch (error) {
      console.error('Failed to save security config:', error);
    }
  }

  async saveEvents(): Promise<void> {
    try {
      await fs.mkdir(path.dirname(this.eventsLogPath), { recursive: true });
      await fs.writeFile(this.eventsLogPath, JSON.stringify(this.events, null, 2));
    } catch (error) {
      console.error('Failed to save security events:', error);
    }
  }

  validateCommand(command: string, args: string[]): {
    blocked: boolean;
    warnings: string[];
    requiredConfirmation: boolean;
  } {
    if (!this.config.enabled) {
      return {
        blocked: false,
        warnings: [],
        requiredConfirmation: false
      };
    }

    const warnings: string[] = [];
    const commandLower = command.toLowerCase();

    for (const rule of this.rules) {
      if (rule.category === 'command' && rule.pattern.test(command)) {
        switch (rule.action) {
          case 'block':
            if (this.config.strictMode) {
              console.log(`🚫 BLOCKED: ${rule.description}`);
              return {
                blocked: true,
                warnings: [],
                requiredConfirmation: false
              };
            }
            break;
          case 'require-confirmation':
            return {
              blocked: false,
              warnings: [`⚠️ ${rule.description}`],
              requiredConfirmation: true
            };
        }
      }
    }

    if (this.config.blocklist.length > 0) {
      for (const blocked of this.config.blocklist) {
        if (commandLower.includes(blocked.toLowerCase())) {
          console.log(`🚫 BLOCKED: Command in blocklist (${blocked})`);
          return {
            blocked: true,
            warnings: [],
            requiredConfirmation: false
          };
        }
      }
    }

    if (!this.config.allowlist.includes(commandLower)) {
      if (this.config.strictMode) {
        warnings.push('⚠️ Command not in allowlist');
      }
    }

    return {
      blocked: false,
      warnings,
      requiredConfirmation: false
    };
  }

  validateInput(input: string): {
    sanitized: string;
    warnings: string[];
    blocked: boolean;
  } {
    if (!this.config.enabled) {
      return {
        sanitized: input,
        warnings: [],
        blocked: false
      };
    }

    const warnings: string[] = [];
    let sanitized = input;

    for (const rule of this.rules) {
      if (rule.category === 'content' && rule.pattern.test(input)) {
        switch (rule.action) {
          case 'sanitize':
            sanitized = input.replace(rule.pattern, '[REDACTED]');
            warnings.push(`🔒 Content pattern matched: ${rule.description}`);
            break;
          case 'block':
            console.log(`🚫 BLOCKED: ${rule.description}`);
            return {
              sanitized: '',
              warnings: [],
              blocked: true
            };
        }
      }
    }

    return {
      sanitized,
      warnings,
      blocked: false
    };
  }

  async validateFilePath(filePath: string): Promise<{ allowed: boolean; warnings: string[] }> {
    const warnings: string[] = [];

    const normalizedPath = path.normalize(filePath);

    for (const rule of this.rules) {
      if (rule.category === 'file' && rule.pattern.test(normalizedPath)) {
        switch (rule.action) {
          case 'block':
            return {
              allowed: false,
              warnings: ['🚫 Path blocked: Protected system directory']
            };
          case 'require-confirmation':
            warnings.push(`⚠️ ${rule.description}`);
            break;
        }
      }
    }

    if (this.config.maxFileSize > 0) {
      try {
        const stats = await fs.stat(normalizedPath);
        const fileSizeMB = stats.size / (1024 * 1024);

        if (fileSizeMB > this.config.maxFileSize) {
          warnings.push(`⚠️ File size warning: ${fileSizeMB.toFixed(2)}MB exceeds limit (${this.config.maxFileSize / (1024 * 1024)}MB)`);
        }
      } catch {
        // File might not exist
      }
    }

    return {
      allowed: warnings.length === 0 || !this.config.strictMode,
      warnings
    };
  }

  async logSecurityEvent(event: Partial<SecurityEvent>): Promise<string> {
    const newEvent: SecurityEvent = {
      id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      event: event.event || 'security_check',
      severity: event.severity || 'medium',
      triggeredBy: 'rule',
      input: event.input || '',
      action: event.action || 'logged',
      blocked: event.blocked || false,
      warning: event.warning || null
    };

    this.events.push(newEvent);
    await this.saveEvents();

    console.log(`🛡️ Security event logged: ${newEvent.id}`);
    return newEvent.id;
  }

  getSecurityEvents(limit: number = 50): SecurityEvent[] {
    return this.events.slice(-limit).reverse();
  }

  getSecuritySummary(): {
    totalEvents: number;
    blockedAttempts: number;
    warningsIssued: number;
    criticalEvents: number;
  } {
    const blocked = this.events.filter(e => e.blocked);
    const warnings = this.events.filter(e => e.warning !== null);
    const critical = this.events.filter(e => e.severity === 'critical');

    return {
      totalEvents: this.events.length,
      blockedAttempts: blocked.length,
      warningsIssued: warnings.length,
      criticalEvents: critical.length
    };
  }

  updateConfig(updates: Partial<SecurityConfig>): void {
    this.config = { ...this.config, ...updates };
    this.saveConfig();
    console.log('🔒 Security configuration updated');
  }

  enable(): void {
    this.config.enabled = true;
    this.saveConfig();
    console.log('🛡️ Security enabled');
  }

  disable(): void {
    this.config.enabled = false;
    this.saveConfig();
    console.log('🔓 Security disabled');
  }

  setStrictMode(strict: boolean): void {
    this.config.strictMode = strict;
    this.saveConfig();
    console.log(`🔒 Strict mode: ${strict ? 'enabled' : 'disabled'}`);
  }

  addToAllowlist(command: string): void {
    if (!this.config.allowlist.includes(command.toLowerCase())) {
      this.config.allowlist.push(command.toLowerCase());
      this.saveConfig();
      console.log(`✅ Added to allowlist: ${command}`);
    }
  }

  addToBlocklist(command: string): void {
    if (!this.config.blocklist.includes(command.toLowerCase())) {
      this.config.blocklist.push(command.toLowerCase());
      this.saveConfig();
      console.log(`🚫 Added to blocklist: ${command}`);
    }
  }

  getConfig(): SecurityConfig {
    return { ...this.config };
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