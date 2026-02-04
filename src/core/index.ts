/**
 * Ultimate Agent Core Systems
 * 
 * Exports all core modules for easy integration
 */

// Core systems
export { OllamaClient, getOllamaClient, resetOllamaClient } from './ollama_integration.js';
export type { 
  OllamaConfig, 
  ChatMessage, 
  ChatRequest, 
  ChatResponse, 
  StreamChunk 
} from './ollama_integration.js';

export { SkillSystem } from './skill_system.js';
export type {
  SkillDefinition,
  SkillInput,
  SkillOutput,
  SkillExecutor
} from './skill_system.js';

export { MemoryManager } from './memory_manager.js';
export type {
  MemoryEntry,
  ConversationState,
  MemoryConfig
} from './memory_manager.js';

export { ErrorHandler, FallbackResponses } from './error_handler.js';
export type {
  ErrorRecord,
  CircuitBreakerState,
  RecoveryStrategy
} from './error_handler.js';

// Unified agent
export { 
  UnifiedAgent, 
  initializeAgent, 
  getAgent, 
  shutdownAgent 
} from './unified_agent.js';
export type {
  AgentConfig,
  AgentRequest,
  AgentResponse
} from './unified_agent.js';

// Version info
export const CORE_VERSION = '2.0.0';
export const CORE_RELEASE_DATE = '2025-02-04';

console.log(`✓ Ultimate Agent Core v${CORE_VERSION} loaded`);
