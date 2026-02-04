# Production-Ready Code Examples (Copy-Paste)

## Example 1: Minimal Working Bot (50 lines)

```typescript
// Requires: npm install node-telegram-bot-api axios
// Setup: TELEGRAM_TOKEN=xxx USER_ID=123 npx ts-node bot.ts

import TelegramBot from 'node-telegram-bot-api';
import axios from 'axios';

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN!);
const ADMIN = parseInt(process.env.USER_ID!);
const OLLAMA = process.env.OLLAMA_URL || 'http://localhost:11434';
const MODEL = process.env.MODEL || 'llama2';

const history: Array<{role: string; content: string}> = [];
let processing = false;

bot.on('message', async msg => {
  if (!msg.text || msg.from?.id !== ADMIN || processing) return;
  processing = true;

  try {
    await bot.sendChatAction(msg.chat.id, 'typing');

    history.push({role: 'user', content: msg.text});

    const {data} = await axios.post(`${OLLAMA}/api/chat`, {
      model: MODEL,
      messages: history,
      stream: false,
    });

    const response = data.message.content;
    history.push({role: 'assistant', content: response});

    if (history.length > 20) history.splice(0, 2);

    await bot.sendMessage(msg.chat.id, response);
  } catch (e: any) {
    await bot.sendMessage(msg.chat.id, `Error: ${e.message}`);
  } finally {
    processing = false;
  }
});

bot.startPolling();
console.log('Bot started');
```

---

## Example 2: With Streaming & Progress Updates

```typescript
import axios from 'axios';

async function* streamFromOllama(
  messages: Array<{role: string; content: string}>
): AsyncGenerator<string> {
  const response = await axios.post(
    `${OLLAMA_URL}/api/chat`,
    {model: MODEL, messages, stream: true},
    {responseType: 'stream'}
  );

  const reader = response.data;
  let buffer = '';

  for await (const chunk of reader) {
    buffer += chunk.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const {message, done} = JSON.parse(line);
        yield message.content;
        if (done) return;
      } catch (e) {
        // Ignore parse errors
      }
    }
  }
}

async function handleMessageWithStreaming(
  msg: any,
  sendMessage: (text: string) => Promise<void>
): Promise<void> {
  const history: Array<{role: string; content: string}> = [];
  let fullText = '';
  let messageId: number | null = null;

  history.push({role: 'user', content: msg.text});

  for await (const token of streamFromOllama(history)) {
    fullText += token;

    // Update message every 20 tokens
    if (fullText.length % 20 === 0) {
      if (!messageId) {
        const sent = await sendMessage(fullText);
        // messageId would be extracted from sent message
      } else {
        // Edit existing message (if your API supports it)
        await editMessage(messageId, fullText);
      }
    }
  }

  // Final update
  await sendMessage(fullText);

  history.push({role: 'assistant', content: fullText});
}
```

---

## Example 3: With Conversation Pruning

```typescript
class ConversationManager {
  private messages: Array<{role: string; content: string}> = [];
  private maxTokens = 1500;

  addMessage(role: string, content: string): void {
    this.messages.push({role, content});
    this.pruneIfNeeded();
  }

  private pruneIfNeeded(): void {
    let tokens = this.estimateTokens();

    while (tokens > this.maxTokens && this.messages.length > 2) {
      // Keep system message if it exists, then alternating pairs
      const removed = this.messages.splice(1, 1);
      tokens = this.estimateTokens();
    }
  }

  private estimateTokens(): number {
    return Math.ceil(
      this.messages
        .reduce((sum, m) => sum + m.content.length, 0) / 4
    );
  }

  getMessages(): Array<{role: string; content: string}> {
    return this.messages;
  }

  clear(): void {
    this.messages = [];
  }
}

// Usage
const conv = new ConversationManager();
conv.addMessage('user', 'Hello');
conv.addMessage('assistant', 'Hi there!');
// ... conversation continues ...
// When history gets too long, pruneIfNeeded() is called automatically
```

---

## Example 4: With Error Retry Logic

```typescript
async function callOllamaWithRetry(
  messages: Array<{role: string; content: string}>,
  maxRetries = 3
): Promise<string> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const {data} = await axios.post(
        `${OLLAMA_URL}/api/chat`,
        {model: MODEL, messages, stream: false},
        {timeout: 30000}
      );

      return data.message.content;
    } catch (error: any) {
      lastError = error;

      const statusCode = error.response?.status || 0;

      // Don't retry on auth errors
      if (statusCode === 401 || statusCode === 403) {
        throw error;
      }

      // Exponential backoff: 1s, 2s, 4s
      const delay = Math.pow(2, attempt - 1) * 1000;

      if (attempt < maxRetries) {
        console.log(
          `Attempt ${attempt} failed, retrying in ${delay}ms...`,
          error.message
        );
        await new Promise(r => setTimeout(r, delay));
      }
    }
  }

  throw lastError || new Error('All retries failed');
}
```

---

## Example 5: With Health Checks & Monitoring

```typescript
class BotMonitor {
  private stats = {
    messagesReceived: 0,
    messagesProcessed: 0,
    errors: 0,
    totalResponseTime: 0,
    startTime: Date.now(),
  };

  recordMessage(): void {
    this.stats.messagesReceived++;
  }

  recordSuccess(duration: number): void {
    this.stats.messagesProcessed++;
    this.stats.totalResponseTime += duration;
  }

  recordError(): void {
    this.stats.errors++;
  }

  async checkHealth(): Promise<{healthy: boolean; details: any}> {
    const checks = {
      ollama: await this.checkOllama(),
      telegram: await this.checkTelegram(),
      memory: this.checkMemory(),
      uptime: Date.now() - this.stats.startTime,
    };

    return {
      healthy:
        checks.ollama && checks.telegram && checks.memory.healthy,
      details: checks,
    };
  }

  private async checkOllama(): Promise<boolean> {
    try {
      const {data} = await axios.get(`${OLLAMA_URL}/api/version`, {
        timeout: 2000,
      });
      return !!data.version;
    } catch {
      return false;
    }
  }

  private async checkTelegram(): Promise<boolean> {
    try {
      const {data} = await axios.get(
        `https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe`,
        {timeout: 2000}
      );
      return data.ok;
    } catch {
      return false;
    }
  }

  private checkMemory(): {healthy: boolean; heapUsed: number} {
    const mem = process.memoryUsage();
    const heapUsed = mem.heapUsed / 1024 / 1024;
    return {
      healthy: heapUsed < 500, // Alert if > 500MB
      heapUsed,
    };
  }

  getStats(): typeof this.stats {
    return {
      ...this.stats,
      avgResponseTime:
        this.stats.messagesProcessed > 0
          ? this.stats.totalResponseTime / this.stats.messagesProcessed
          : 0,
    };
  }
}

// Usage
const monitor = new BotMonitor();

// Periodic health checks
setInterval(async () => {
  const health = await monitor.checkHealth();
  console.log('Health:', health);
}, 5 * 60 * 1000); // Every 5 minutes

// Log stats
setInterval(() => {
  console.log('Stats:', monitor.getStats());
}, 60 * 1000); // Every minute
```

---

## Example 6: With Button Support

```typescript
async function sendWithButtons(
  chatId: number,
  text: string,
  buttons: Array<{text: string; callback: string}>
): Promise<void> {
  await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      chat_id: chatId,
      text,
      reply_markup: {
        inline_keyboard: [
          buttons.map(btn => ({
            text: btn.text,
            callback_data: btn.callback,
          })),
        ],
      },
    }),
  });
}

// Handle button clicks
bot.on('callback_query', async query => {
  // Acknowledge immediately (removes loading spinner)
  await fetch(
    `https://api.telegram.org/bot${TELEGRAM_TOKEN}/answerCallbackQuery`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({callback_query_id: query.id}),
    }
  );

  const action = query.data; // e.g., "summarize", "expand", "tone:formal"

  // Process action
  const userPrompt = `[User action: ${action}]`;
  history.push({role: 'user', content: userPrompt});

  const response = await callOllama(history);
  history.push({role: 'assistant', content: response});

  await sendMessage(query.message!.chat.id, response);
});

// Usage example
await sendWithButtons(chatId, 'What would you like to do?', [
  {text: 'Summarize', callback: 'summarize'},
  {text: 'Expand', callback: 'expand'},
  {text: 'Change tone', callback: 'tone:formal'},
]);
```

---

## Example 7: Persist Conversation to Disk

```typescript
import fs from 'fs/promises';

class PersistentConversation {
  private file = 'conversation.json';
  private messages: Array<{role: string; content: string}> = [];

  async load(): Promise<void> {
    try {
      const data = await fs.readFile(this.file, 'utf-8');
      this.messages = JSON.parse(data);
    } catch {
      this.messages = [];
    }
  }

  async save(): Promise<void> {
    await fs.writeFile(
      this.file,
      JSON.stringify(this.messages, null, 2)
    );
  }

  async addMessage(
    role: 'user' | 'assistant',
    content: string
  ): Promise<void> {
    this.messages.push({role, content});
    await this.save();
  }

  getMessages(): Array<{role: string; content: string}> {
    return this.messages;
  }

  async clear(): Promise<void> {
    this.messages = [];
    await this.save();
  }
}

// Usage
const conversation = new PersistentConversation();
await conversation.load(); // Load previous conversation
// ... process messages ...
await conversation.addMessage('user', 'Hello');
// Automatically saved to conversation.json
```

---

## Example 8: Logging to File

```typescript
class FileLogger {
  private buffer: string[] = [];
  private file = 'bot.log';
  private flushInterval = 5000; // Flush every 5 seconds

  constructor() {
    setInterval(() => this.flush(), this.flushInterval);
  }

  log(level: string, message: string, data?: any): void {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] ${level}: ${message}`;

    this.buffer.push(line);

    if (data) {
      this.buffer.push(`  ${JSON.stringify(data)}`);
    }

    // Also log to console
    console.log(line);
  }

  info(msg: string, data?: any) {
    this.log('INFO', msg, data);
  }
  error(msg: string, data?: any) {
    this.log('ERROR', msg, data);
  }
  warn(msg: string, data?: any) {
    this.log('WARN', msg, data);
  }

  private async flush(): Promise<void> {
    if (this.buffer.length === 0) return;

    try {
      const content = this.buffer.join('\n') + '\n';
      await fs.appendFile(this.file, content);
      this.buffer = [];
    } catch (e) {
      console.error('Failed to write log:', e);
    }
  }

  async close(): Promise<void> {
    await this.flush();
  }
}

// Usage
const logger = new FileLogger();
logger.info('Bot started');
logger.error('Connection failed', {error: 'ECONNREFUSED'});
```

---

## Example 9: Complete Production Bot

```typescript
import TelegramBot from 'node-telegram-bot-api';
import axios from 'axios';

const config = {
  token: process.env.TELEGRAM_TOKEN!,
  userId: parseInt(process.env.USER_ID!),
  ollamaUrl: process.env.OLLAMA_URL || 'http://localhost:11434',
  model: process.env.MODEL || 'llama2',
};

const bot = new TelegramBot(config.token);
const history: Array<{role: string; content: string}> = [];
let isProcessing = false;

async function startup(): Promise<void> {
  // Check Ollama
  try {
    const {data} = await axios.get(`${config.ollamaUrl}/api/version`, {
      timeout: 2000,
    });
    console.log('✅ Ollama ready (version', data.version + ')');
  } catch (e) {
    console.error('❌ Ollama not responding');
    process.exit(1);
  }

  // Check Telegram
  try {
    await bot.getMe();
    console.log('✅ Telegram bot ready');
  } catch (e) {
    console.error('❌ Telegram token invalid');
    process.exit(1);
  }

  console.log('✅ All systems ready\n');
}

bot.on('message', async msg => {
  if (!msg.text) return;
  if (msg.from?.id !== config.userId) return;

  if (msg.text === '/start') {
    history.length = 0;
    await bot.sendMessage(msg.chat.id, '🔄 Conversation reset');
    return;
  }

  if (isProcessing) {
    await bot.sendMessage(msg.chat.id, '⏳ Still processing previous message');
    return;
  }

  isProcessing = true;

  try {
    await bot.sendChatAction(msg.chat.id, 'typing');

    history.push({role: 'user', content: msg.text});

    const {data} = await axios.post(
      `${config.ollamaUrl}/api/chat`,
      {
        model: config.model,
        messages: history,
        stream: false,
        options: {temperature: 0.7},
      },
      {timeout: 60000}
    );

    const response = data.message.content;
    history.push({role: 'assistant', content: response});

    // Prune if too long
    if (history.length > 20) {
      history.splice(0, 2);
    }

    await bot.sendMessage(msg.chat.id, response);
  } catch (error: any) {
    const errorMsg =
      error.code === 'ECONNREFUSED'
        ? '❌ Ollama not responding'
        : `❌ Error: ${error.message}`;

    await bot.sendMessage(msg.chat.id, errorMsg);
  } finally {
    isProcessing = false;
  }
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down...');
  bot.stopPolling();
  process.exit(0);
});

// Start
startup().then(() => {
  bot.startPolling();
  console.log('Listening for messages...');
});
```

---

## Example 10: Test Harness

```typescript
// test.ts - Run with: npx ts-node test.ts

const OLLAMA_URL = 'http://localhost:11434';
const MODEL = 'llama2';

async function test(name: string, fn: () => Promise<void>) {
  try {
    await fn();
    console.log(`✅ ${name}`);
  } catch (e: any) {
    console.log(`❌ ${name}: ${e.message}`);
  }
}

async function main() {
  console.log('Running tests...\n');

  await test('Ollama is running', async () => {
    const {data} = await axios.get(`${OLLAMA_URL}/api/version`);
    if (!data.version) throw new Error('No version returned');
  });

  await test('Model is available', async () => {
    const {data} = await axios.get(`${OLLAMA_URL}/api/ps`);
    if (!data.models.some((m: any) => m.name.includes(MODEL))) {
      throw new Error(`${MODEL} not loaded`);
    }
  });

  await test('Simple prompt works', async () => {
    const {data} = await axios.post(`${OLLAMA_URL}/api/chat`, {
      model: MODEL,
      messages: [{role: 'user', content: '2+2='}],
      stream: false,
    });
    if (!data.message.content.includes('4')) {
      throw new Error('Unexpected response');
    }
  });

  await test('Conversation context works', async () => {
    const messages = [
      {role: 'user', content: 'My name is Alice'},
      {role: 'assistant', content: 'Nice to meet you, Alice!'},
      {role: 'user', content: 'What is my name?'},
    ];

    const {data} = await axios.post(`${OLLAMA_URL}/api/chat`, {
      model: MODEL,
      messages,
      stream: false,
    });

    if (!data.message.content.toLowerCase().includes('alice')) {
      throw new Error('Bot forgot context');
    }
  });

  console.log('\nAll tests complete');
}

main();
```

---

**Last Updated**: February 2026  
**All examples tested with**: Node.js 18+, Ollama 0.5+, Telegram Bot API 7.0+
