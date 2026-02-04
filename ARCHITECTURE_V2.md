# Ultimate Agent Core Architecture v2.0

## Overview

The Ultimate Agent now features a sophisticated, modular architecture with four interconnected core systems designed for 2025-2026 LLM applications. Each system is independently functional but deeply integrated through a unified orchestration layer.

```
┌─────────────────────────────────────────────────────────┐
│          Unified Agent Orchestrator                     │
│  (Coordinates all systems, manages conversations)       │
└────────────┬────────────┬────────────┬────────────┬─────┘
             │            │            │            │
    ┌────────▼───┐  ┌─────▼──┐  ┌──────▼───┐  ┌────▼─────┐
    │ Ollama      │  │ Skill  │  │ Memory   │  │ Error    │
    │ Integration │  │ System │  │ Manager  │  │ Handler  │
    └────────────┘  └────────┘  └──────────┘  └──────────┘
         │              │            │             │
         ├─ Chat API    ├─ Routing   ├─ Storage   ├─ Recovery
         ├─ Streaming   ├─ Chaining  ├─ Recall    ├─ Circuit
         ├─ Embeddings  ├─ Priority  ├─ Context   ├─ Fallback
         └─ Models      └─ Weights   └─ Analytics └─ Analytics
```

## System 1: Ollama Integration (`ollama_integration.ts`)

**Purpose**: Direct, efficient communication with Ollama local LLM server

### Key Features
- **Proper API Conformance**: Implements Ollama API v1 spec (2025)
- **Response Streaming**: Real-time token-by-token responses
- **Automatic Retries**: Exponential backoff with jitter (3 attempts)
- **Request Caching**: 5-minute cache for identical requests
- **Health Monitoring**: Continuous availability checks
- **Token Analytics**: Tracks tokens/second and performance metrics

### Core Methods
```typescript
// Send complete request (non-streaming)
await ollama.chat(messages, { model, stream: false })

// Stream response chunks as they arrive
for await (const chunk of ollama.chatStream(messages)) {
  console.log(chunk);
}

// Generate embeddings for semantic search
const embeddings = await ollama.embed(text);

// Model management
const models = await ollama.listModels();
const info = await ollama.getModelInfo('llama2');

// Health check
const healthy = await ollama.healthCheck();
```

### Error Handling
- **Network Errors**: Automatic retry with exponential backoff
- **Model Not Found**: Clear error message with pull command
- **Server Errors (5xx)**: Retryable with circuit breaker protection
- **Timeouts**: Configurable timeout with graceful degradation
- **Connection Issues**: Helpful diagnostic messages

### Performance
- Average response time: 2-5 seconds (depends on model size)
- Streaming reduces perceived latency
- Caching eliminates duplicate API calls
- Token counting enables cost/performance analysis

## System 2: Skill System (`skill_system.ts`)

**Purpose**: Dynamic, context-aware task routing and execution

### Architecture
Skills are modular, composable units of work that can be:
- **Registered Dynamically**: Add new skills at runtime
- **Ranked by Relevance**: Intelligent routing based on task description
- **Chained Together**: Execute sequences of related skills
- **Weighted by Performance**: Learns from success/failure patterns

### Built-in Skills
1. **Code Generation** (`skill_code`): Generate clean, documented code
2. **Code Analysis** (`skill_analyze`): Review quality and complexity
3. **Test Generation** (`skill_test`): Create unit tests
4. **Debugging** (`skill_debug`): Find and fix issues
5. **Learning** (`skill_learn`): Explain concepts clearly

### Core Methods
```typescript
// Execute single skill
const result = await skills.executeSkill('skill_code', input);

// Intelligent routing (auto-select best skill)
const output = await skills.routeTask(userMessage, input);

// Chain skills together (output of one feeds into next)
const chain = await skills.chainSkills(
  ['skill_code', 'skill_test', 'skill_analyze'],
  initialInput
);

// Register custom skill
skills.registerSkill(definition, async (input) => {
  // Your skill implementation
  return { success: true, result: '...' };
});
```

### Skill Routing Algorithm
1. **Keyword Matching**: Scan task for skill-specific keywords
2. **Weight Scoring**: Apply historical performance weights
3. **Ranking**: Sort by relevance score
4. **Fallback**: Try next best skill if first fails
5. **Chaining**: Execute follow-up skills automatically

### Performance Tracking
- Execution time per skill
- Success/failure rates
- Dynamic weight adjustment (faster executions boost weight)
- Skill dependency resolution
- Circular dependency prevention

## System 3: Memory Manager (`memory_manager.ts`)

**Purpose**: Intelligent conversation persistence and context management

### Features

#### Conversation Management
- **Session-based**: Separate conversations per user
- **Context Window**: Efficiently manages last N messages
- **Memory Compression**: Auto-summarizes old messages to save space
- **Persistence**: Auto-saves conversations every 5 minutes

#### Semantic Search
- **Embedding Generation**: Creates simple word-frequency embeddings
- **Cosine Similarity**: Finds relevant past messages
- **Context Recall**: Automatically includes relevant history
- **Conversation Topics**: Tracks conversation subject

#### Storage
- **In-Memory**: Fast access during conversation
- **Disk Persistence**: JSON export for long-term storage
- **Compression**: Summarizes old messages to reduce size
- **Export/Import**: Full conversation export for analysis

### Core Methods
```typescript
// Create or resume session
const session = memory.getOrCreateSession(userId, sessionId);

// Add message to memory
const entry = memory.addMessage(sessionId, 'user', content);

// Get active context for LLM
const contextMessages = memory.getContextWindow(sessionId);

// Find similar past messages
const similar = memory.retrieveSimilar(sessionId, query, limit: 5);

// Update conversation context (topic, sentiment, etc)
memory.updateContext(sessionId, { topic: 'coding', sentiment: 'positive' });

// Export conversation
await memory.exportSession(sessionId);
```

### Memory Optimization
- **Max Size**: 10MB per session (configurable)
- **Context Window**: Last 50 messages (configurable)
- **Compression Threshold**: Auto-compress at 100+ messages
- **Token Tracking**: Counts approximate tokens for efficiency
- **Importance Scoring**: Keeps high-importance messages

### Semantic Recall
```
Query: "How did we handle database errors?"
├─ Generate embedding from query
├─ Compare to all past messages (cosine similarity)
├─ Return top-5 most similar entries
└─ Include context in next LLM call
```

## System 4: Error Handler (`error_handler.ts`)

**Purpose**: Robust error handling with intelligent recovery

### Components

#### Error Categorization
- **Network**: Connection refused, timeout
- **API**: 404 not found, 500 server error
- **Auth**: Authentication/authorization failures
- **Resource**: Memory, quota, rate limits
- **Parsing**: Invalid JSON, malformed responses

#### Circuit Breaker Pattern
```
         ┌─────────────┐
         │ CLOSED      │
         │ (OK)        │
         └──────┬──────┘
                │ failures >= 5
                ▼
         ┌─────────────┐
         │ OPEN        │
         │ (Failing)   │
         └──────┬──────┘
                │ timeout (60s)
                ▼
         ┌─────────────┐
         │ HALF-OPEN   │
         │ (Testing)   │
         └──────┬──────┘
                │ success >= 2
                ▼
             CLOSED
```

#### Recovery Strategies
Each error type has prioritized recovery strategies:

1. **ConnectionRetry** (Priority: 10)
   - Waits 1 second and retries
   - For ECONNREFUSED, timeouts

2. **TimeoutRetry** (Priority: 9)
   - Waits 2 seconds and retries
   - For timeout-related errors

3. **DemoModeFallback** (Priority: 1)
   - Switches to demo/offline mode
   - Returns pre-generated responses
   - Always available as last resort

### Core Methods
```typescript
// Handle error with automatic recovery
const result = await errorHandler.handleError(error, context);

// Record success/failure for circuit breaker
errorHandler.recordSuccess('service_name');
errorHandler.recordFailure('service_name');

// Check if circuit is open
const isOpen = errorHandler.isCircuitOpen('service_name');

// Register custom recovery strategy
errorHandler.registerStrategy({
  name: 'CustomRecovery',
  priority: 8,
  canHandle: (err) => err.message.includes('specific'),
  execute: async () => { /* recovery logic */ }
});

// Get error statistics
const stats = errorHandler.getStats();
```

## System 5: Unified Agent Orchestrator (`unified_agent.ts`)

**Purpose**: Coordinates all systems into cohesive whole

### Integration Points
- **Message Processing**: Routes through skills with memory context
- **Event Coordination**: All systems emit events via unified agent
- **Configuration**: Single config object for all systems
- **Lifecycle**: Initialize, process, shutdown in orchestrated fashion

### Process Flow
```
User Message
     │
     ▼
Add to Memory (user role)
     │
     ▼
Get Context Window from Memory
     │
     ▼
Route to Skill System
     │
     ├─ Extract topic/urgency
     ├─ Rank applicable skills
     └─ Execute best skill
     │
     ▼
Add Response to Memory (assistant role)
     │
     ▼
Return Response to User
```

### API
```typescript
// Initialize agent
const agent = await initializeAgent({
  userId: 'user123',
  model: 'llama2',
  enableMemory: true,
  enableSkills: true,
  enableErrorHandling: true
});

// Process message (complete end-to-end)
const response = await agent.processMessage({
  userMessage: 'Fix this bug: ...',
  allowChaining: true
});

// Stream response (for real-time updates)
for await (const chunk of agent.streamResponse(request)) {
  console.log(chunk);
}

// Get conversation info
const info = agent.getConversationInfo();

// Get statistics
const stats = agent.getStats();
// {
//   ollama: { model, requestCount, avgDuration, ... },
//   skills: { totalExecutions, successful, failed, ... },
//   memory: { sessionCount, totalMessages, totalTokens, ... },
//   errors: { totalErrors, resolved, resolutionRate, ... }
// }

// Graceful shutdown
await agent.shutdown();
```

## Configuration

### Environment Variables
```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=60000

# Memory Configuration
MEMORY_MAX_SIZE=10485760
MEMORY_CONTEXT_WINDOW=50

# Error Handling
ERROR_LOG_PATH=./logs/errors.log
ERROR_RETRY_ATTEMPTS=3

# Demo Mode
DEMO_MODE=false
```

### Programmatic Configuration
```typescript
const config: AgentConfig = {
  userId: 'user123',
  sessionId: 'session_abc123', // Optional: resume session
  model: 'llama2', // Ollama model name
  ollamaConfig: {
    baseURL: 'http://localhost:11434',
    model: 'llama2'
  },
  enableMemory: true,
  enableSkills: true,
  enableErrorHandling: true,
  demoMode: false
};

const agent = await initializeAgent(config);
```

## Usage Examples

### Basic Chat
```typescript
const response = await agent.processMessage({
  userMessage: 'Write a TypeScript function to reverse an array'
});

console.log(response.content);
// Generated TypeScript code with explanations
```

### With Skill Chaining
```typescript
const response = await agent.processMessage({
  userMessage: 'Create a Node.js REST API for a todo app',
  allowChaining: true
});

// Automatically chains: code → test → analyze
```

### Streaming Response
```typescript
let fullResponse = '';
for await (const chunk of agent.streamResponse({
  userMessage: 'Explain async/await in JavaScript'
})) {
  process.stdout.write(chunk);
  fullResponse += chunk;
}
```

### Custom Skill
```typescript
skills.registerSkill({
  id: 'skill_security',
  name: 'Security Audit',
  description: 'Analyze code for security issues',
  category: 'analysis',
  priority: 'high',
  enabled: true,
  version: '1.0.0'
}, async (input) => {
  // Custom implementation
  return {
    success: true,
    result: 'Security analysis...',
    chained: []
  };
});
```

## Monitoring & Analytics

### Real-time Events
```typescript
agent.on('messageProcessed', (response) => {
  console.log(`Processed in ${response.duration}ms`);
  console.log(`Skills used: ${response.skillsUsed.join(', ')}`);
  console.log(`Confidence: ${response.confidence}`);
});

agent.on('skillEvent', (event) => {
  console.log(`Skill: ${event.data.skillId}`);
});

agent.on('errorEvent', (event) => {
  console.log(`Error recovered: ${event.data.record.recovery}`);
});
```

### Statistics Endpoint
```typescript
const stats = agent.getStats();
// {
//   ollama: {
//     model: 'llama2',
//     requestCount: 150,
//     avgDuration: 2500,
//     maxDuration: 8000,
//     cacheSize: 45
//   },
//   skills: {
//     skillCount: 6,
//     totalExecutions: 45,
//     successful: 42,
//     failed: 3,
//     successRate: 93.3
//   },
//   memory: {
//     sessionCount: 1,
//     totalMessages: 89,
//     totalTokens: 28500,
//     memorySize: 114 // KB
//   },
//   errors: {
//     totalErrors: 5,
//     resolved: 4,
//     resolutionRate: 80,
//     byCategory: { network: 2, timeout: 2, parsing: 1 }
//   },
//   uptime: 3600 // seconds
// }
```

## Best Practices

### 1. Session Management
- Always use `userId` for conversation continuity
- Optionally provide `sessionId` to resume specific conversation
- Conversations auto-save to disk every 5 minutes

### 2. Memory Management
- Context window of 50 messages balances quality and efficiency
- Messages auto-compress after 100 entries
- Use `memory.retrieveSimilar()` for context recall

### 3. Error Handling
- Circuit breaker auto-enables for failing services
- Recovery attempts happen automatically
- Check `stats.errors.resolutionRate` for health

### 4. Performance
- Cache eliminates duplicate calls (5-min TTL)
- Streaming responses feel faster to users
- Skills can execute in parallel with chaining

### 5. Extensibility
- Register custom skills dynamically
- Implement custom recovery strategies
- Subscribe to events for monitoring

## Migration from Old System

The old system used `RealQwenClient` with OpenAI SDK. Here's the migration path:

### Old Code
```typescript
const client = new RealQwenClient();
const response = await client.chat('Your prompt');
```

### New Code
```typescript
const agent = await initializeAgent({
  userId: 'user1',
  model: 'llama2'
});

const response = await agent.processMessage({
  userMessage: 'Your prompt'
});
```

### Key Differences
| Aspect | Old | New |
|--------|-----|-----|
| Initialization | Sync | Async |
| Model | Single, fixed | Configurable, switchable |
| Memory | None | Built-in with compression |
| Skills | None | Dynamic routing & chaining |
| Error Handling | Basic | Advanced with recovery |
| Streaming | Limited | Full support |
| Analytics | Basic | Comprehensive |

## Troubleshooting

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama
ollama serve

# Pull required model
ollama pull llama2
```

### Memory Issues
- Check `stats.memory.totalTokens` (default 10MB limit)
- Messages auto-compress at 100 entries
- Export old conversations: `await agent.exportConversation()`

### Skill Not Executing
- Check if skill is enabled: `skills.setSkillEnabled(skillId, true)`
- Verify task keywords match skill routing
- Check execution history: `skills.getSkillStats(skillId)`

### High Response Latency
- Check if model is loaded: `ollama ps`
- Monitor token/second in stats
- Consider switching to smaller model
- Enable caching for repeated requests

## Architecture Decisions

### Why Modular?
- **Independence**: Each system can be updated/fixed separately
- **Testability**: Easy to unit test each module
- **Flexibility**: Use only needed systems
- **Scalability**: Can replace modules without rewrite

### Why Event-Based?
- **Decoupling**: Systems don't directly depend on each other
- **Monitoring**: Global visibility into all operations
- **Extensibility**: Add listeners for custom logic
- **Resilience**: Failures don't cascade

### Why Circuit Breaker?
- **Stability**: Prevents cascading failures
- **Degradation**: Gracefully switches to fallback
- **Recovery**: Auto-attempts when service recovers
- **Transparency**: Clear failure states

### Why Memory Compression?
- **Efficiency**: Keeps large conversations manageable
- **Context**: Summarizes old messages for recall
- **Performance**: Reduces token count for LLM calls
- **Quality**: Maintains conversation coherence

## Future Enhancements

### Q2 2025
- [ ] Agentic loop with autonomous task execution
- [ ] Multi-user conversation federation
- [ ] Advanced embedding model integration
- [ ] Persistent vector database backend

### Q3 2025
- [ ] Fine-tuning support for custom models
- [ ] Token-level cost optimization
- [ ] Advanced prompt engineering framework
- [ ] Conversation analysis and insights

### Q4 2025
- [ ] Graph-based conversation reasoning
- [ ] Multi-modal support (images, audio)
- [ ] Distributed agent network
- [ ] Enterprise deployment toolkit

## Contributing

To add new features:
1. Create feature in appropriate system module
2. Add events for monitoring/integration
3. Update stats/analytics
4. Document in this file
5. Test with Telegram bot integration

## Support

For issues, questions, or contributions:
- Check troubleshooting section
- Review event logs: `./logs/errors.log`
- Export conversation for analysis: `await agent.exportConversation()`
- Check GitHub issues for known problems

---

**Version**: 2.0.0  
**Released**: February 4, 2025  
**Maintainers**: Ultimate Agent Team
