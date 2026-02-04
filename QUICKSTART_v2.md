# Quick Start Guide - Ultimate Agent v2.0

## 5-Minute Setup

### 1. Verify Ollama is Running
```bash
# Check Ollama service
curl http://localhost:11434/api/version

# If not running, start it
ollama serve

# Ensure model is available
ollama pull llama2
```

### 2. Configure Environment
```bash
# Create .env file in project root
cat > .env << 'EOF'
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=60000
DEMO_MODE=false
EOF
```

### 3. Import in Your Code

```typescript
import { 
  initializeAgent, 
  getAgent, 
  shutdownAgent 
} from './src/core/index.js';

// Initialize
const agent = await initializeAgent({
  userId: 'user123',
  model: 'llama2',
  enableMemory: true,
  enableSkills: true,
  enableErrorHandling: true
});

// Use
const response = await agent.processMessage({
  userMessage: 'Write a function to reverse an array in TypeScript'
});

console.log(response.content);

// Shutdown
await agent.shutdown();
```

## Common Use Cases

### Chat with Memory
```typescript
const response = await agent.processMessage({
  userMessage: 'Write a REST API'
});

// Second message will have context from first
const response2 = await agent.processMessage({
  userMessage: 'Now add authentication'
});
```

### Force Specific Skill
```typescript
const response = await agent.processMessage({
  userMessage: 'Check this code',
  forceSkill: 'skill_analyze' // Use code analyzer
});
```

### Stream Response (Real-time)
```typescript
let fullResponse = '';
for await (const chunk of agent.streamResponse({
  userMessage: 'Explain async/await'
})) {
  process.stdout.write(chunk);
  fullResponse += chunk;
}
```

### Get Statistics
```typescript
const stats = agent.getStats();
console.log(stats);
// {
//   ollama: { model, requestCount, avgDuration, ... },
//   skills: { skillCount, executions, success, ... },
//   memory: { sessionCount, messages, tokens, ... },
//   errors: { totalErrors, resolved, rate, ... }
// }
```

### Export Conversation
```typescript
const filepath = await agent.exportConversation();
console.log(`Saved to: ${filepath}`);
```

## Monitor in Real-Time

```typescript
// Listen to skill execution
agent.on('skillEvent', (event) => {
  console.log(`Skill: ${event.data.skillId}`);
});

// Listen to errors
agent.on('errorEvent', (event) => {
  console.log(`Error recovered: ${event.data.record.recovery}`);
});

// Listen to completed messages
agent.on('messageProcessed', (response) => {
  console.log(`Response in ${response.duration}ms`);
  console.log(`Skills used: ${response.skillsUsed.join(', ')}`);
  console.log(`Confidence: ${response.confidence}`);
});
```

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Start Ollama
ollama serve

# Verify connection
curl http://localhost:11434/api/version
# Should return: {"version":"0.x.x"}
```

### "Model not found"
```bash
# Pull the model
ollama pull llama2

# Verify it exists
ollama list
```

### High latency
```typescript
// Check if model is loaded
const stats = agent.getStats();
console.log(stats.ollama.avgDuration);

// If over 5 seconds, model might be loading
// Warm up with one request, then try again

// Or switch to smaller model
await shutdownAgent();
const agent = await initializeAgent({
  userId: 'user123',
  model: 'neural-chat' // Smaller, faster
});
```

### Memory issues
```typescript
// Check memory usage
const stats = agent.getStats();
console.log(stats.memory.totalTokens);

// Export old conversations
const filepath = await agent.exportConversation();

// Clear in-memory state but keep disk persistence
await agent.reset();
```

## Integration with Telegram Bot

```typescript
import { Telegraf } from 'telegraf';
import { initializeAgent, shutdownAgent } from './src/core/index.js';

const bot = new Telegraf(process.env.TELEGRAM_TOKEN!);
let agent;

// Initialize on start
bot.start(async (ctx) => {
  if (!agent) {
    agent = await initializeAgent({
      userId: ctx.from.id.toString(),
      model: 'llama2'
    });
  }
  await ctx.reply('Agent ready!');
});

// Process messages
bot.on('message', async (ctx) => {
  try {
    const response = await agent!.processMessage({
      userMessage: ctx.message.text || '',
      allowChaining: true
    });

    await ctx.reply(response.content);
  } catch (error) {
    await ctx.reply('Error: ' + (error as Error).message);
  }
});

// Graceful shutdown
process.on('SIGINT', async () => {
  if (agent) {
    await shutdownAgent();
  }
  process.exit(0);
});

bot.launch();
```

## Configuration Reference

### Agent Config
```typescript
interface AgentConfig {
  userId: string;                    // Required: User ID
  sessionId?: string;                // Optional: Resume session
  model?: string;                    // LLM model name
  ollamaConfig?: {                   // Ollama settings
    baseURL: string;                 // http://localhost:11434
    model: string;                   // llama2
  };
  enableMemory?: boolean;            // Conversation memory (default: true)
  enableSkills?: boolean;            // Skill routing (default: true)
  enableErrorHandling?: boolean;     // Error recovery (default: true)
  demoMode?: boolean;                // Demo/offline mode (default: false)
}
```

### Environment Variables
```bash
OLLAMA_BASE_URL=http://localhost:11434     # Ollama server
OLLAMA_MODEL=llama2                        # Default model
OLLAMA_TIMEOUT=60000                       # Request timeout ms

MEMORY_MAX_SIZE=10485760                   # 10MB per session
MEMORY_CONTEXT_WINDOW=50                   # Last 50 messages

ERROR_LOG_PATH=./logs/errors.log          # Error log location
ERROR_RETRY_ATTEMPTS=3                     # Retry count

DEMO_MODE=false                            # Use demo responses
```

## API Reference (Quick)

### Initialize
```typescript
const agent = await initializeAgent(config);
```

### Process Message
```typescript
const response = await agent.processMessage({
  userMessage: string;
  context?: string;
  forceSkill?: string;
  allowChaining?: boolean;
});

// Returns:
{
  id: string;
  timestamp: number;
  content: string;                  // AI response
  skillsUsed: string[];            // Which skills ran
  duration: number;                // Response time ms
  confidence: number;              // 0-1 confidence score
  metadata?: Record<string, any>;
}
```

### Stream Response
```typescript
for await (const chunk of agent.streamResponse(request)) {
  // chunk is a string piece of the response
}
```

### Get Info
```typescript
agent.getConversationInfo()    // Current session info
agent.getStats()               // All statistics
```

### Shutdown
```typescript
await agent.shutdown()         // Graceful cleanup
```

## Performance Tips

### 1. Use Streaming for Long Responses
```typescript
// Better UX for users
for await (const chunk of agent.streamResponse(request)) {
  console.log(chunk); // Print in real-time
}
```

### 2. Cache Repeated Requests
- Automatic 5-minute cache
- Identical messages within 5 min use cache
- No additional configuration needed

### 3. Use Skill Chaining
```typescript
const response = await agent.processMessage({
  userMessage: 'Write and test an API',
  allowChaining: true // Auto-chains related skills
});
```

### 4. Monitor Circuit Breaker
```typescript
const stats = agent.getStats();
console.log(stats.errors.circuitStates);

// If any are "open", Ollama is failing
// Check logs and restart Ollama if needed
```

### 5. Regular Exports
```typescript
// Export old conversations to free memory
setInterval(async () => {
  const filepath = await agent.exportConversation();
  console.log(`Exported to ${filepath}`);
}, 24 * 60 * 60 * 1000); // Daily
```

## Testing

### Quick Test
```typescript
import { initializeAgent, shutdownAgent } from './src/core/index.js';

async function test() {
  const agent = await initializeAgent({
    userId: 'test-user',
    model: 'llama2'
  });

  try {
    const response = await agent.processMessage({
      userMessage: 'Say hello'
    });

    console.log('✅ Success:', response.content.substring(0, 100));
  } catch (error) {
    console.error('❌ Failed:', error);
  } finally {
    await shutdownAgent();
  }
}

test();
```

### Validate Setup
```bash
# 1. Check Ollama
curl http://localhost:11434/api/version

# 2. Check model
ollama list

# 3. Check pull works
ollama pull llama2

# 4. Try direct API
curl http://localhost:11434/api/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "hi"}],
    "stream": false
  }'
```

## Need Help?

1. **Check Logs**
   ```
   ./logs/errors.log    # Error log
   ```

2. **Verify Setup**
   ```bash
   ollama serve
   curl http://localhost:11434/api/version
   ```

3. **Check Stats**
   ```typescript
   console.log(agent.getStats());
   ```

4. **Read Docs**
   - `ARCHITECTURE_V2.md` - Full system design
   - `IMPLEMENTATION_COMPLETE_v2.md` - What was built

5. **Enable Demo Mode**
   ```typescript
   const agent = await initializeAgent({
     userId: 'user1',
     demoMode: true  // Use mock responses
   });
   ```

---

**Version**: 2.0.0  
**Last Updated**: February 4, 2025  
**Status**: ✅ Production Ready
