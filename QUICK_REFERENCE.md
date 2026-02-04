# Quick Reference: Common Patterns & Checklists

## 1. OLLAMA RESPONSE FORMATS (Quick Lookup)

### `/api/chat` - Recommended for Conversation ✅

**Streaming (default)** - Get tokens as they generate:
```
PAYLOAD: {"model": "llama2", "messages": [...], "stream": true}
RESPONSE: Stream of newline-separated JSON objects
├─ {"model":"llama2", "message":{"role":"assistant","content":"The"}, "done":false}
├─ {"model":"llama2", "message":{"role":"assistant","content":" sky"}, "done":false}
└─ {"model":"llama2", "message":{...}, "done":true, "eval_count":25, ...}
```

**Non-streaming** - Get full response at once:
```
PAYLOAD: {"model": "llama2", "messages": [...], "stream": false}
RESPONSE: {"model":"llama2", "message":{"role":"assistant","content":"Full response..."}, "done":true, ...}
```

### `/api/generate` - For Simple Completions (NOT Conversation) ⚠️

**WRONG for conversation!** This endpoint doesn't preserve context.
```
DON'T USE: ollama.generate({prompt: "hello", stream: true})
DO USE:    ollama.chat({messages: [{role: "user", content: "hello"}]})
```

---

## 2. TELEGRAM BOT API ESSENTIALS

### Response Codes to Handle

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Proceed |
| 400 | Bad Request | Check parameters |
| 401 | Unauthorized | Check token |
| 429 | Rate Limited | Wait `retry_after` seconds |
| 500+ | Server Error | Retry with exponential backoff |

### Rate Limits (Hard Limits)
- **30 messages/sec per chat** - After exceeding, returns 429
- **Callback query timeout** - Must answer within 30 seconds
- **Polling timeout** - Use `timeout: 25` (seconds) for long-polling

### How to Fix "Bot didn't respond"
```typescript
// ❌ WRONG - User sees timeout spinner for 30 seconds
await processExpensiveOperation(); // Takes 45 seconds
await bot.answerCallbackQuery(query.id);

// ✅ RIGHT - Acknowledge immediately
await bot.answerCallbackQuery(query.id);
// Then process in background
processExpensiveOperation().catch(log);
```

---

## 3. CONVERSATION STATE MACHINE

### Valid State Transitions
```
[IDLE] ← → [PROCESSING] → [WAITING_USER_INPUT] → [PROCESSING] → [IDLE]
  ↓
[ERROR] → [IDLE]
```

### Implementation
```typescript
enum BotState {
  IDLE = 'idle',
  PROCESSING = 'processing',
  ERROR = 'error',
}

// ✅ Always transition atomically
private setState(newState: BotState): void {
  this.state = newState;
}

// ✅ Check before processing
if (this.state === BotState.PROCESSING) {
  return; // Queue or reject
}
```

---

## 4. TOKEN COUNTING (Estimate, Not Exact)

### Quick Formulas
```
English text:  tokens ≈ characters / 4
              OR tokens ≈ words × 1.3

For estimation: Add 20% buffer to be safe
```

### When to Prune
```
Token budget = (Model's max context - 1000 buffer) / 2

If sum of messages > budget, remove oldest messages
```

### Example (7B model with 2K context)
```
Available: 2048 tokens
Buffer: 1000
Usable: 1048 tokens

If conversation = 900 tokens → OK
If conversation = 1100 tokens → Prune oldest messages
```

---

## 5. MESSAGE QUEUE PATTERN (Prevent Race Conditions)

### The Problem
```typescript
// ❌ WRONG - Race condition
handleMessage(msg) {
  await callOllama(msg); // Takes 2 seconds
}

// User sends 3 messages in quick succession
// All 3 call Ollama simultaneously - chaos!
```

### The Solution
```typescript
// ✅ RIGHT - Sequential queue
private queue: Message[] = [];
private isProcessing = false;

async handleMessage(msg: Message): void {
  this.queue.push(msg);
  if (!this.isProcessing) {
    await this.processQueue();
  }
}

private async processQueue(): void {
  this.isProcessing = true;
  while (this.queue.length > 0) {
    const msg = this.queue.shift()!;
    await this.processMessage(msg);
  }
  this.isProcessing = false;
}
```

---

## 6. ERROR RECOVERY PATTERNS

### Ollama Connection Errors

```typescript
async function callOllamaWithRetry(
  prompt: string,
  maxRetries = 3
): Promise<string> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await callOllama(prompt);
    } catch (error) {
      if (attempt === maxRetries) throw error;
      
      const delay = Math.pow(2, attempt) * 1000; // 2s, 4s, 8s
      console.log(`Retry ${attempt}/${maxRetries} after ${delay}ms`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

### Telegram Rate Limiting

```typescript
const RATE_LIMIT_DELAY = {
  '429': (retryAfter: number) => retryAfter * 1000,
  default: (attempt: number) => Math.pow(2, attempt) * 1000,
};

async function sendWithRateLimit(
  chatId: number,
  text: string
): Promise<void> {
  try {
    await sendMessage(chatId, text);
  } catch (error: any) {
    if (error.response?.status === 429) {
      const retryAfter = error.response.parameters?.retry_after || 2;
      await new Promise(r => 
        setTimeout(r, retryAfter * 1000)
      );
      await sendWithRateLimit(chatId, text); // Recursive retry
    } else {
      throw error;
    }
  }
}
```

---

## 7. STREAMING RESPONSE HANDLING

### Complete Pattern

```typescript
async function* streamOllamaResponse(
  messages: Message[]
): AsyncGenerator<string> {
  const response = await fetch(
    `${OLLAMA_URL}/api/chat`,
    {
      method: 'POST',
      body: JSON.stringify({ model, messages, stream: true }),
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) throw new Error(`HTTP ${response.status}`);

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  try {
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines[lines.length - 1];

      for (let i = 0; i < lines.length - 1; i++) {
        if (!lines[i].trim()) continue;
        
        try {
          const parsed = JSON.parse(lines[i]);
          yield parsed.message.content;
          if (parsed.done) return;
        } catch (e) {
          console.error('Parse error:', lines[i]);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Usage
let fullResponse = '';
for await (const token of streamOllamaResponse(messages)) {
  fullResponse += token;
  // Update UI every 20 tokens
  if (fullResponse.length % 20 === 0) {
    updateUI(fullResponse);
  }
}
```

---

## 8. SINGLE-USER BOT SETUP

### Configuration
```typescript
// Instead of database, just use environment variables
const ADMIN_ID = parseInt(process.env.ADMIN_USER_ID);
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;

// Conversation history in memory (auto-GC after restart)
const conversationHistory: Message[] = [];
```

### Startup Checklist
```typescript
async function startup() {
  // 1. Validate config
  if (!ADMIN_ID) throw new Error('ADMIN_USER_ID missing');
  
  // 2. Check Ollama
  const ollama = await fetch(`${OLLAMA_URL}/api/version`);
  if (!ollama.ok) throw new Error('Ollama not running');
  
  // 3. Check Telegram
  const tg = await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe`);
  if (!tg.ok) throw new Error('Invalid Telegram token');
  
  // 4. Pre-load model
  await fetch(`${OLLAMA_URL}/api/chat`, {
    method: 'POST',
    body: JSON.stringify({ model, messages: [] }),
  });
  
  console.log('✅ All systems ready');
}
```

---

## 9. DEBUGGING CHECKLIST

### Bot Not Responding

- [ ] Is Ollama running? `curl http://localhost:11434/api/version`
- [ ] Is model loaded? `ollama ps`
- [ ] Is Telegram token valid? `curl https://api.telegram.org/bot<TOKEN>/getMe`
- [ ] Is user ID correct? `echo $ADMIN_USER_ID`
- [ ] Are logs showing errors? `tail -f bot.log | grep ERROR`

### Messages Sent But No Response

- [ ] Check if bot marked as processing: `isProcessing = true`?
- [ ] Is conversation history being updated?
- [ ] Is Ollama returning empty response? Add logging: `console.log(response)`
- [ ] Is message too long? `messages.join(',').length > 4000`

### Slow Responses

- [ ] Check Ollama load time: Look for `load_duration` in response
- [ ] Check generation time: `eval_duration / eval_count`
- [ ] Is model loaded or being loaded from disk? `curl http://localhost:11434/api/ps`
- [ ] Reduce context by pruning more aggressively

### Memory Leaks

- [ ] Are old message objects being garbage collected? Use `--inspect` and Chrome DevTools
- [ ] Are event listeners properly removed? Check `bot.removeAllListeners()`
- [ ] Is fetch reader released? `reader.releaseLock()` called?

---

## 10. PERFORMANCE BENCHMARKS

### Expected Latencies (Local 7B Model, No GPU)

| Operation | Min | Typical | Max |
|-----------|-----|---------|-----|
| Model load | 1s | 3-5s | 15s |
| First response | 2s | 5s | 10s |
| Per token | 20ms | 50ms | 100ms |
| Telegram API call | 50ms | 100ms | 500ms |
| Total for "Hello" | 3s | 6s | 12s |

### How to Optimize

```typescript
// 1. Keep model in memory (don't unload)
keepAlive: '24h'

// 2. Use lower temperature for faster inference
temperature: 0.3 // Lower = faster and more deterministic

// 3. Limit output tokens
options: { num_predict: 100 } // Max 100 tokens per response

// 4. Reduce context length
// Prune aggressively to keep under 500 tokens

// 5. Use GPU acceleration
// Ollama auto-uses GPU if available
```

---

## 11. PRODUCTION DEPLOYMENT CHECKLIST

- [ ] **Environment Variables**
  - [ ] `TELEGRAM_TOKEN` set
  - [ ] `ADMIN_USER_ID` set
  - [ ] `OLLAMA_URL` set (use internal IP, not localhost)
  - [ ] `NODE_ENV=production`

- [ ] **Error Handling**
  - [ ] All promises have `.catch()`
  - [ ] Logging to file (not just stdout)
  - [ ] Health check endpoint running
  - [ ] Graceful shutdown on SIGTERM

- [ ] **Monitoring**
  - [ ] Response time tracking
  - [ ] Error rate monitoring
  - [ ] Memory usage alerts (>500MB)
  - [ ] Ollama connection status

- [ ] **Backup & Recovery**
  - [ ] Conversation history saved to disk
  - [ ] Can restore from backup
  - [ ] Automatic restart on crash

- [ ] **Security**
  - [ ] User ID validation on every request
  - [ ] No sensitive data in logs
  - [ ] HTTPS for Telegram (if webhook)
  - [ ] Firewall blocks Ollama port (only localhost)

---

## 12. COMMON MISTAKES & FIXES

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using `/api/generate` | Bot forgets previous messages | Switch to `/api/chat` |
| No message queue | Messages get jumbled | Add queue with `isProcessing` flag |
| Not pruning history | "Prompt too long" error | Implement token counting + pruning |
| Missing callback ACK | Telegram shows loading spinner forever | Call `answerCallbackQuery` immediately |
| No error handling | Bot crashes silently | Wrap all async in try-catch |
| Memory leak in streams | RAM usage grows | Always call `reader.releaseLock()` |
| Race condition | Duplicate responses | Add mutex/semaphore |
| Wrong endpoint | "Model not found" | Check URL: `:11434` not `:8000` |

---

## 13. RESOURCES & LINKS

### Official Documentation
- **Ollama API**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Node.js Fetch**: https://nodejs.org/api/fetch.html (v18+)

### Community Examples
- **Ollama Discord**: https://discord.gg/ollama
- **Telegram Dev Community**: https://t.me/tg_dev
- **GitHub: telegram-ollama-bot**: Search GitHub for working examples

### Tools
- **Ollama Web UI**: http://localhost:3000 (web interface)
- **Telegram Bot Tester**: @BotFather on Telegram
- **JSON Validator**: https://jsonlint.com/ (test API responses)

---

## 14. MINIMAL TEMPLATE (Copy-Paste Ready)

```typescript
const TOKEN = process.env.TELEGRAM_TOKEN;
const USER_ID = parseInt(process.env.USER_ID);
const OLLAMA = 'http://localhost:11434';
const MODEL = 'llama2';

const history = [];
let isProcessing = false;

async function send(chatId, text) {
  await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({chat_id: chatId, text}),
  });
}

async function handleMessage(msg) {
  if (msg.from.id !== USER_ID || isProcessing) return;
  isProcessing = true;

  try {
    history.push({role: 'user', content: msg.text});

    const res = await fetch(`${OLLAMA}/api/chat`, {
      method: 'POST',
      body: JSON.stringify({model: MODEL, messages: history, stream: false}),
    });

    const {message} = await res.json();
    history.push({role: 'assistant', content: message.content});

    if (history.length > 20) history.splice(0, 2);
    
    await send(msg.chat.id, message.content);
  } catch (e) {
    await send(msg.chat.id, `Error: ${e.message}`);
  } finally {
    isProcessing = false;
  }
}

// Poll for updates
async function poll() {
  let offset = 0;
  while (true) {
    const res = await fetch(
      `https://api.telegram.org/bot${TOKEN}/getUpdates?offset=${offset}`
    );
    const {result} = await res.json();
    for (const {update_id, message, callback_query} of result) {
      if (message) await handleMessage(message);
      offset = update_id + 1;
    }
  }
}

poll();
```

---

**Last Updated**: February 2026  
**Tested With**: Node.js 18+, Ollama 0.5+, Telegram Bot API v7.0+
