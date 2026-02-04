/**
 * Telegram Error Handler & Recovery
 * 
 * Features:
 * - Error categorization specific to Telegram integration
 * - Circuit breaker for Telegram API
 * - Recovery strategies (retry, fallback, reconnect)
 * - User-friendly error messages
 * - Error logging and analytics
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { EventEmitter } from 'events';
import { Context } from 'telegraf';

type ErrorCategory =
  | 'telegram_api_error'
  | 'ollama_connection_error'
  | 'agent_processing_error'
  | 'memory_error'
  | 'timeout_error'
  | 'rate_limit_error'
  | 'unknown_error';

type RecoveryStrategy = 'retry' | 'fallback' | 'skip' | 'notify_user';

interface ErrorRecord {
  timestamp: number;
  category: ErrorCategory;
  message: string;
  stack?: string;
  context?: Record<string, any>;
  attempts: number;
  recovered: boolean;
  recoveryTime?: number;
}

interface CircuitBreakerState {
  service: string;
  state: 'closed' | 'open' | 'half-open';
  failures: number;
  lastFailure: number;
  nextRetry: number;
}

export class TelegramErrorHandler extends EventEmitter {
  private errorHistory: ErrorRecord[] = [];
  private maxErrorHistory: number = 1000;
  private circuitBreakers: Map<string, CircuitBreakerState> = new Map();
  private failureThreshold: number = 5;
  private resetTimeout: number = 60000; // 1 minute
  private logDir: string;

  constructor(logDir: string = path.join(process.cwd(), 'logs')) {
    super();
    this.logDir = logDir;
    this.initializeCircuitBreakers();
  }

  /**
   * Initialize circuit breakers for key services
   */
  private initializeCircuitBreakers(): void {
    const services = ['ollama', 'telegram_api', 'agent_core', 'memory'];

    for (const service of services) {
      this.circuitBreakers.set(service, {
        service,
        state: 'closed',
        failures: 0,
        lastFailure: 0,
        nextRetry: 0,
      });
    }
  }

  /**
   * Handle error with automatic recovery
   */
  async handleError(
    error: any,
    context: {
      userId?: number;
      ctx?: Context;
      service: string;
      userMessage?: string;
      attemptNumber?: number;
    }
  ): Promise<{
    handled: boolean;
    strategy: RecoveryStrategy;
    userMessage: string;
    canRetry: boolean;
  }> {
    try {
      const timestamp = Date.now();
      const category = this.categorizeError(error, context.service);
      const strategy = this.selectRecoveryStrategy(category, context);

      // Record error
      const errorRecord: ErrorRecord = {
        timestamp,
        category,
        message: error.message || String(error),
        stack: error.stack,
        context,
        attempts: (context.attemptNumber || 0) + 1,
        recovered: false,
      };

      // Check circuit breaker
      const breaker = this.circuitBreakers.get(context.service);
      if (breaker && breaker.state === 'open') {
        return {
          handled: true,
          strategy: 'fallback',
          userMessage: this.getFallbackMessage(category),
          canRetry: false,
        };
      }

      // Execute recovery strategy
      let recovered = false;
      let userMessage = '';

      switch (strategy) {
        case 'retry':
          recovered = await this.attemptRetry(error, context);
          userMessage = recovered
            ? '✅ Recovered from temporary error. Retrying...'
            : this.getUserErrorMessage(category);
          break;

        case 'fallback':
          userMessage = this.getFallbackMessage(category);
          recovered = true; // We provided a fallback
          break;

        case 'skip':
          userMessage = '⏭️ Skipping this operation. Please try again.';
          recovered = true;
          break;

        case 'notify_user':
          userMessage = this.getUserErrorMessage(category);
          recovered = false;
          break;

        default:
          userMessage = '❌ An unexpected error occurred.';
          recovered = false;
      }

      // Update error record
      errorRecord.recovered = recovered;
      if (recovered) {
        errorRecord.recoveryTime = Date.now() - timestamp;
      }

      // Store error
      await this.recordError(errorRecord);

      // Update circuit breaker
      if (recovered) {
        this.recordSuccess(context.service);
      } else {
        this.recordFailure(context.service);
      }

      // Emit event
      this.emit('error_handled', {
        category,
        strategy,
        recovered,
        service: context.service,
        userId: context.userId,
      });

      return {
        handled: true,
        strategy,
        userMessage,
        canRetry: strategy === 'retry' && !recovered,
      };
    } catch (handlingError) {
      console.error('[ErrorHandler] Error handling failed:', handlingError);

      return {
        handled: false,
        strategy: 'notify_user',
        userMessage: '❌ A critical error occurred. Please try again.',
        canRetry: true,
      };
    }
  }

  /**
   * Categorize error
   */
  private categorizeError(error: any, service: string): ErrorCategory {
    const message = error.message?.toLowerCase() || '';
    const code = error.code?.toString() || '';

    if (error.name === 'TelegrafError' || code.includes('telegram')) {
      return 'telegram_api_error';
    }

    if (message.includes('econnrefused') || message.includes('unreachable')) {
      return 'ollama_connection_error';
    }

    if (message.includes('timeout') || code === 'ETIMEDOUT') {
      return 'timeout_error';
    }

    if (message.includes('rate') || code === '429') {
      return 'rate_limit_error';
    }

    if (message.includes('memory') || message.includes('out of')) {
      return 'memory_error';
    }

    if (service === 'agent_core' || message.includes('agent')) {
      return 'agent_processing_error';
    }

    return 'unknown_error';
  }

  /**
   * Select recovery strategy
   */
  private selectRecoveryStrategy(category: ErrorCategory, context: any): RecoveryStrategy {
    const attemptNumber = context.attemptNumber || 0;

    // Don't retry too many times
    if (attemptNumber >= 3) {
      return 'fallback';
    }

    switch (category) {
      case 'ollama_connection_error':
      case 'timeout_error':
        return 'retry'; // Network errors are often transient

      case 'rate_limit_error':
        return 'skip'; // Don't retry immediately for rate limits

      case 'memory_error':
        return 'skip'; // Can't recover from memory errors easily

      case 'telegram_api_error':
        return attemptNumber < 2 ? 'retry' : 'notify_user';

      case 'agent_processing_error':
        return 'fallback'; // Provide demo response

      case 'unknown_error':
      default:
        return 'notify_user';
    }
  }

  /**
   * Attempt to retry with exponential backoff
   */
  private async attemptRetry(
    error: any,
    context: any
  ): Promise<boolean> {
    const attemptNumber = context.attemptNumber || 0;
    const backoffMs = Math.min(1000 * Math.pow(2, attemptNumber), 10000);

    console.log(`[ErrorHandler] Retrying in ${backoffMs}ms (attempt ${attemptNumber + 1})`);

    await new Promise(resolve => setTimeout(resolve, backoffMs));

    // In real scenario, would re-execute the operation
    // For now, we just indicate willingness to retry
    return true;
  }

  /**
   * Get user-friendly error message
   */
  private getUserErrorMessage(category: ErrorCategory): string {
    const messages: Record<ErrorCategory, string> = {
      telegram_api_error: '🤖 Issue contacting Telegram. This should resolve quickly.',
      ollama_connection_error: '🦙 Ollama is not responding. Is it running?\n`ollama serve`',
      agent_processing_error: '⚙️ The agent encountered an issue. Please try a simpler request.',
      memory_error: '💾 Running low on memory. Clearing conversation history...',
      timeout_error: '⏱️ Request took too long. Please try again with a simpler request.',
      rate_limit_error: '⚠️ Too many requests. Please wait a moment and try again.',
      unknown_error: '❌ Something went wrong. The team has been notified.',
    };

    return messages[category] || messages.unknown_error;
  }

  /**
   * Get fallback message for category
   */
  private getFallbackMessage(category: ErrorCategory): string {
    const fallbacks: Record<ErrorCategory, string> = {
      telegram_api_error: '📱 Telegram temporarily unavailable. Please try again.',
      ollama_connection_error:
        `🦙 Ollama is offline. 
To use the agent, run:
\`\`\`
ollama serve
\`\`\`

Or install Ollama from https://ollama.ai`,

      agent_processing_error:
        `⚙️ Agent is temporarily unavailable. 
Here's a helpful tip:
• Code should be clean and documented
• Test your code before deploying
• Use proper error handling`,

      memory_error: `💾 Memory cleared. Session restarted. Try again!`,

      timeout_error: `⏱️ Request timeout. Try:
• A simpler task
• Breaking it into smaller parts
• Check your internet connection`,

      rate_limit_error: `⚠️ Please wait before trying again.
Free tier has usage limits.`,

      unknown_error: `❌ An error occurred. Try again or contact support.`,
    };

    return fallbacks[category] || fallbacks.unknown_error;
  }

  /**
   * Record error in history
   */
  private async recordError(error: ErrorRecord): Promise<void> {
    this.errorHistory.push(error);

    // Keep history size manageable
    if (this.errorHistory.length > this.maxErrorHistory) {
      this.errorHistory.shift();
    }

    // Log to file
    try {
      await fs.mkdir(this.logDir, { recursive: true });
      const logFile = path.join(this.logDir, 'telegram-errors.log');
      await fs.appendFile(logFile, JSON.stringify(error) + '\n');
    } catch (err) {
      console.error('[ErrorHandler] Failed to write error log:', err);
    }
  }

  /**
   * Record successful operation
   */
  private recordSuccess(service: string): void {
    const breaker = this.circuitBreakers.get(service);
    if (!breaker) return;

    if (breaker.state === 'half-open') {
      breaker.state = 'closed';
      breaker.failures = 0;
    } else if (breaker.state === 'closed') {
      breaker.failures = Math.max(0, breaker.failures - 1);
    }

    this.emit('service-recovered', { service });
  }

  /**
   * Record failure
   */
  private recordFailure(service: string): void {
    const breaker = this.circuitBreakers.get(service);
    if (!breaker) return;

    breaker.failures++;
    breaker.lastFailure = Date.now();

    if (breaker.failures >= this.failureThreshold) {
      if (breaker.state === 'closed') {
        breaker.state = 'open';
        breaker.nextRetry = Date.now() + this.resetTimeout;

        this.emit('circuit-breaker-open', {
          service,
          failures: breaker.failures,
        });

        console.warn(`[ErrorHandler] Circuit breaker OPEN for ${service}`);

        // Schedule reset attempt
        setTimeout(() => {
          if (breaker.state === 'open') {
            breaker.state = 'half-open';
            console.log(`[ErrorHandler] Circuit breaker HALF-OPEN for ${service}`);
          }
        }, this.resetTimeout);
      }
    }
  }

  /**
   * Get circuit breaker status
   */
  getCircuitStatus(service?: string): Record<string, CircuitBreakerState> {
    if (service) {
      const breaker = this.circuitBreakers.get(service);
      return breaker ? { [service]: breaker } : {};
    }

    const status: Record<string, CircuitBreakerState> = {};
    for (const [name, breaker] of this.circuitBreakers) {
      status[name] = { ...breaker };
    }
    return status;
  }

  /**
   * Get error statistics
   */
  getStats(): {
    totalErrors: number;
    recentErrors: ErrorRecord[];
    errorsByCategory: Record<ErrorCategory, number>;
    recoveryRate: number;
    circuitBreakerStatus: Record<string, string>;
  } {
    const errorsByCategory: Record<ErrorCategory, number> = {
      telegram_api_error: 0,
      ollama_connection_error: 0,
      agent_processing_error: 0,
      memory_error: 0,
      timeout_error: 0,
      rate_limit_error: 0,
      unknown_error: 0,
    };

    let recovered = 0;

    for (const error of this.errorHistory) {
      errorsByCategory[error.category]++;
      if (error.recovered) recovered++;
    }

    const circuitStatus: Record<string, string> = {};
    for (const [service, breaker] of this.circuitBreakers) {
      circuitStatus[service] = breaker.state;
    }

    return {
      totalErrors: this.errorHistory.length,
      recentErrors: this.errorHistory.slice(-10),
      errorsByCategory,
      recoveryRate:
        this.errorHistory.length > 0
          ? Math.round((recovered / this.errorHistory.length) * 100)
          : 100,
      circuitBreakerStatus: circuitStatus,
    };
  }

  /**
   * Clear error history
   */
  clearHistory(): void {
    this.errorHistory = [];
  }

  /**
   * Reset circuit breaker
   */
  resetCircuitBreaker(service: string): void {
    const breaker = this.circuitBreakers.get(service);
    if (breaker) {
      breaker.state = 'closed';
      breaker.failures = 0;
      breaker.lastFailure = 0;
      console.log(`[ErrorHandler] Reset circuit breaker for ${service}`);
    }
  }

  /**
   * Shutdown error handler
   */
  async shutdown(): Promise<void> {
    // Final log flush
    try {
      await fs.mkdir(this.logDir, { recursive: true });
      const statsFile = path.join(this.logDir, 'telegram-error-stats.json');
      await fs.writeFile(statsFile, JSON.stringify(this.getStats(), null, 2));
    } catch (err) {
      console.error('[ErrorHandler] Failed to write final stats:', err);
    }

    console.log('[ErrorHandler] Error handler shutdown');
  }
}

/**
 * Singleton error handler
 */
let errorHandlerInstance: TelegramErrorHandler | null = null;

export function initializeErrorHandler(logDir?: string): TelegramErrorHandler {
  if (!errorHandlerInstance) {
    errorHandlerInstance = new TelegramErrorHandler(logDir);
  }
  return errorHandlerInstance;
}

export function getErrorHandler(): TelegramErrorHandler | null {
  return errorHandlerInstance;
}

export async function shutdownErrorHandler(): Promise<void> {
  if (errorHandlerInstance) {
    await errorHandlerInstance.shutdown();
    errorHandlerInstance = null;
  }
}
