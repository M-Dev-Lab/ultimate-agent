/**
 * Unified Agent Integration Layer
 * Combines all systems: Ollama, Skills, Memory, Error Handling
 * 
 * This is the main orchestrator that ties everything together
 */

import { OllamaClient, ChatMessage, getOllamaClient } from './ollama_integration.js';
import { SkillSystem, SkillInput, SkillOutput } from './skill_system.js';
import { MemoryManager, ConversationState } from './memory_manager.js';
import { ErrorHandler, FallbackResponses } from './error_handler.js';
import { EventEmitter } from 'events';

// ============= TYPES =============

export interface AgentConfig {
  userId: string;
  sessionId?: string;
  model?: string;
  ollamaConfig?: {
    baseURL: string;
    model: string;
  };
  enableMemory?: boolean;
  enableSkills?: boolean;
  enableErrorHandling?: boolean;
  demoMode?: boolean;
}

export interface AgentRequest {
  userMessage: string;
  context?: string;
  forceSkill?: string;
  allowChaining?: boolean;
}

export interface AgentResponse {
  id: string;
  timestamp: number;
  content: string;
  skillsUsed: string[];
  duration: number;
  confidence: number;
  suggestedFollowUp?: string;
  metadata?: Record<string, any>;
}

// ============= UNIFIED AGENT =============

export class UnifiedAgent extends EventEmitter {
  private config: AgentConfig;
  private ollama: OllamaClient;
  private skills: SkillSystem;
  private memory: MemoryManager;
  private errorHandler: ErrorHandler;
  private isInitialized: boolean = false;
  private requestId: number = 0;

  constructor(config: AgentConfig) {
    super();
    this.config = config;

    // Initialize all systems
    this.ollama = getOllamaClient(config.ollamaConfig);
    this.skills = new SkillSystem(this.ollama);
    this.memory = new MemoryManager({
      contextWindow: 50,
      enableSemanticIndex: true
    });
    this.errorHandler = new ErrorHandler();

    // Setup event listeners
    this.setupEventListeners();

    console.log(`✓ Unified Agent initialized for user: ${config.userId}`);
  }

  /**
   * Initialize agent asynchronously
   */
  async init(): Promise<boolean> {
    try {
      // Check Ollama health
      const healthy = await this.ollama.healthCheck();
      if (!healthy && !this.config.demoMode) {
        console.warn('⚠️  Ollama not available, enabling demo mode');
        this.config.demoMode = true;
      }

      // Initialize or restore session
      const sessionId = this.config.sessionId || undefined;
      this.memory.getOrCreateSession(this.config.userId, sessionId);

      this.isInitialized = true;
      this.emit('initialized');
      return true;
    } catch (error) {
      console.error('Initialization failed:', error);
      return false;
    }
  }

  /**
   * Process user message end-to-end
   */
  async processMessage(request: AgentRequest): Promise<AgentResponse> {
    const requestId = ++this.requestId;
    const startTime = Date.now();
    const skillsUsed: string[] = [];

    try {
      // Get conversation session
      const session = this.memory.getOrCreateSession(this.config.userId);

      // Add user message to memory
      this.memory.addMessage(session.sessionId, 'user', request.userMessage);

      // Get context window
      const contextMessages = this.memory.getContextWindow(session.sessionId);

      // Route to appropriate skill or use routing
      let skillOutput: SkillOutput | null = null;

      if (request.forceSkill) {
        // Use specific skill
        skillOutput = await this.skills.executeSkill(request.forceSkill, {
          context: request.userMessage,
          parameters: {
            contextMessages,
            userContext: request.context
          },
          sessionId: session.sessionId,
          userId: this.config.userId
        });
        skillsUsed.push(request.forceSkill);
      } else {
        // Intelligent skill routing
        skillOutput = await this.skills.routeTask(request.userMessage, {
          context: request.userMessage,
          parameters: {
            contextMessages,
            userContext: request.context
          },
          sessionId: session.sessionId,
          userId: this.config.userId
        });

        if (skillOutput.skillId !== 'none') {
          skillsUsed.push(skillOutput.skillId);

          // Chain if requested
          if (request.allowChaining && skillOutput.chained?.length) {
            const chainedResults = await this.skills.chainSkills(
              skillOutput.chained,
              {
                context: skillOutput.result || request.userMessage,
                parameters: { previousOutput: skillOutput },
                sessionId: session.sessionId,
                userId: this.config.userId
              }
            );
            skillsUsed.push(...chainedResults.map(r => r.skillId));
          }
        }
      }

      // Get final response content
      let responseContent: string;

      if (skillOutput?.success && skillOutput.result) {
        responseContent = skillOutput.result;
      } else if (this.config.demoMode) {
        responseContent = FallbackResponses.getDemoCodeResponse(request.userMessage);
      } else {
        // Fallback to direct Ollama call
        const response = await this.ollama.chat([
          ...contextMessages,
          { role: 'user', content: request.userMessage }
        ]);
        responseContent = response.message.content;
      }

      // Add response to memory
      this.memory.addMessage(session.sessionId, 'assistant', responseContent);

      // Calculate confidence
      const confidence = this.calculateConfidence(skillOutput, responseContent);

      const duration = Date.now() - startTime;

      const agentResponse: AgentResponse = {
        id: `resp_${requestId}_${Date.now()}`,
        timestamp: Date.now(),
        content: responseContent,
        skillsUsed,
        duration,
        confidence,
        metadata: {
          skillOutput,
          sessionId: session.sessionId,
          contextSize: contextMessages.length
        }
      };

      // Update context
      this.memory.updateContext(session.sessionId, {
        topic: this.extractTopic(request.userMessage),
        urgency: this.extractUrgency(request.userMessage)
      });

      this.emit('messageProcessed', agentResponse);
      this.errorHandler.recordSuccess('agent_processing');

      return agentResponse;
    } catch (error) {
      const duration = Date.now() - startTime;

      // Handle error
      await this.errorHandler.handleError(error, {
        requestId,
        userMessage: request.userMessage,
        skillsAttempted: skillsUsed
      });

      this.errorHandler.recordFailure('agent_processing');

      // Return fallback response
      return {
        id: `resp_${requestId}_error`,
        timestamp: Date.now(),
        content: FallbackResponses.getOfflineResponse(),
        skillsUsed: [],
        duration,
        confidence: 0.3,
        metadata: {
          error: error instanceof Error ? error.message : String(error),
          fallback: true
        }
      };
    }
  }

  /**
   * Get streaming response (for real-time updates)
   */
  async *streamResponse(request: AgentRequest): AsyncGenerator<string, void, unknown> {
    try {
      const session = this.memory.getOrCreateSession(this.config.userId);
      const contextMessages = this.memory.getContextWindow(session.sessionId);

      // Add user message
      this.memory.addMessage(session.sessionId, 'user', request.userMessage);

      // Stream from Ollama
      let fullContent = '';
      for await (const chunk of this.ollama.chatStream([
        ...contextMessages,
        { role: 'user', content: request.userMessage }
      ])) {
        fullContent += chunk;
        yield chunk;
      }

      // Save complete response to memory
      this.memory.addMessage(session.sessionId, 'assistant', fullContent);

      this.errorHandler.recordSuccess('agent_stream');
    } catch (error) {
      await this.errorHandler.handleError(error);
      this.errorHandler.recordFailure('agent_stream');
      yield FallbackResponses.getOfflineResponse();
    }
  }

  /**
   * Get conversation summary and context
   */
  getConversationInfo(): {
    sessionId: string;
    messageCount: number;
    topic?: string;
    duration: number;
    lastMessage: string;
  } {
    const session = this.memory.getOrCreateSession(this.config.userId);
    const summary = this.memory.getSummary(session.sessionId);

    return {
      sessionId: session.sessionId,
      messageCount: summary.messageCount,
      topic: summary.topic,
      duration: summary.duration,
      lastMessage: summary.lastMessage
    };
  }

  /**
   * Export conversation
   */
  async exportConversation(): Promise<string> {
    const session = this.memory.getOrCreateSession(this.config.userId);
    return await this.memory.exportSession(session.sessionId);
  }

  /**
   * Get agent statistics
   */
  getStats() {
    return {
      ollama: this.ollama.getStats(),
      skills: this.skills.getSkillStats(),
      memory: this.memory.getStats(),
      errors: this.errorHandler.getStats(),
      uptime: process.uptime()
    };
  }

  /**
   * Shutdown agent gracefully
   */
  async shutdown(): Promise<void> {
    try {
      await this.memory.shutdown();
      await this.errorHandler.shutdown();
      await this.ollama.reset();
      this.isInitialized = false;
      console.log('✓ Agent shutdown complete');
    } catch (error) {
      console.error('Error during shutdown:', error);
    }
  }

  // ============= PRIVATE HELPERS =============

  /**
   * Setup event listeners across systems
   */
  private setupEventListeners(): void {
    this.ollama.on('chatComplete', (data) => {
      this.emit('ollamaEvent', { type: 'chatComplete', data });
    });

    this.skills.on('skillExecuted', (data) => {
      this.emit('skillEvent', { type: 'skillExecuted', data });
    });

    this.errorHandler.on('errorRecovered', (data) => {
      this.emit('errorEvent', { type: 'errorRecovered', data });
    });
  }

  /**
   * Calculate confidence in response
   */
  private calculateConfidence(skillOutput: SkillOutput | null, content: string): number {
    let confidence = 0.7; // Base confidence

    // Boost if skill was used and successful
    if (skillOutput?.success) {
      confidence += 0.15;
    }

    // Reduce if error recovery was needed
    if (!skillOutput?.success) {
      confidence -= 0.2;
    }

    // Boost if response is substantial
    if (content.length > 200) {
      confidence += 0.05;
    }

    return Math.max(0, Math.min(1, confidence));
  }

  /**
   * Extract topic from message
   */
  private extractTopic(message: string): string | undefined {
    const topics = ['code', 'debug', 'api', 'database', 'ui', 'test', 'deploy', 'security'];

    for (const topic of topics) {
      if (message.toLowerCase().includes(topic)) {
        return topic;
      }
    }

    return undefined;
  }

  /**
   * Extract urgency from message
   */
  private extractUrgency(message: string): 'low' | 'normal' | 'high' | 'critical' {
    const urgencyKeywords = {
      critical: ['critical', 'urgent', 'immediately', 'asap', 'now'],
      high: ['urgent', 'important', 'important', 'soon'],
      normal: ['please', 'can you', 'help']
    };

    const lower = message.toLowerCase();

    if (urgencyKeywords.critical.some(k => lower.includes(k))) {
      return 'critical';
    }
    if (urgencyKeywords.high.some(k => lower.includes(k))) {
      return 'high';
    }

    return 'normal';
  }
}

// ============= SINGLETON INSTANCE =============

let agentInstance: UnifiedAgent | null = null;

export async function initializeAgent(config: AgentConfig): Promise<UnifiedAgent> {
  if (!agentInstance) {
    agentInstance = new UnifiedAgent(config);
    const success = await agentInstance.init();
    if (!success) {
      console.warn('⚠️  Agent initialized in degraded mode');
    }
  }
  return agentInstance;
}

export function getAgent(): UnifiedAgent {
  if (!agentInstance) {
    throw new Error('Agent not initialized. Call initializeAgent first.');
  }
  return agentInstance;
}

export async function shutdownAgent(): Promise<void> {
  if (agentInstance) {
    await agentInstance.shutdown();
    agentInstance = null;
  }
}

export default UnifiedAgent;
