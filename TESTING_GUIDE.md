# Testing Guide for Telegram + Ollama Bot

## Unit Testing

### Test File: `bot.test.ts`

```typescript
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import TelegramOllamaBot from './bot';

describe('TelegramOllamaBot', () => {
  let bot: TelegramOllamaBot;
  let mockTelegram: any;
  let mockOllama: any;

  beforeEach(() => {
    // Mock Telegram API
    mockTelegram = {
      sendMessage: jest.fn().mockResolvedValue({}),
      sendChatAction: jest.fn().mockResolvedValue({}),
      answerCallbackQuery: jest.fn().mockResolvedValue({}),
    };

    // Mock Ollama
    mockOllama = {
      chat: jest.fn().mockResolvedValue({
        message: { content: 'Test response' },
      }),
    };

    bot = new TelegramOllamaBot(mockTelegram, mockOllama);
  });

  describe('Message Processing', () => {
    it('should add user message to history', async () => {
      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: 'Hello',
      };

      await bot.handleMessage(msg);

      const history = bot.getHistory();
      expect(history).toContainEqual({
        role: 'user',
        content: 'Hello',
      });
    });

    it('should call Ollama with full conversation history', async () => {
      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: 'Hello',
      };

      await bot.handleMessage(msg);

      expect(mockOllama.chat).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: expect.arrayContaining([
            { role: 'user', content: 'Hello' },
          ]),
        })
      );
    });

    it('should not process if already processing', async () => {
      // Simulate long-running response
      mockOllama.chat.mockImplementation(
        () => new Promise(resolve => 
          setTimeout(() => resolve({ message: { content: 'Response' } }), 1000)
        )
      );

      const msg = { from: { id: 123 }, chat: { id: 123 }, text: 'Test' };

      // Start first message (will hang)
      const p1 = bot.handleMessage(msg);

      // Try second message immediately
      const p2 = bot.handleMessage(msg);

      // Reset mock to allow p1 to complete
      mockOllama.chat.mockResolvedValue({ message: { content: 'Response' } });

      // Only one should process
      await Promise.all([p1, p2]);
      expect(mockOllama.chat).toHaveBeenCalledTimes(1);
    });

    it('should prune conversation history when exceeding max length', async () => {
      // Add 15 messages (assuming max is 10)
      for (let i = 0; i < 15; i++) {
        const msg = {
          from: { id: 123 },
          chat: { id: 123 },
          text: `Message ${i}`,
        };
        await bot.handleMessage(msg);
      }

      const history = bot.getHistory();
      expect(history.length).toBeLessThanOrEqual(20); // 10 exchanges * 2 (user + assistant)
    });

    it('should handle /start command and reset history', async () => {
      // Add message first
      let msg = { from: { id: 123 }, chat: { id: 123 }, text: 'Hello' };
      await bot.handleMessage(msg);
      expect(bot.getHistory().length).toBeGreaterThan(0);

      // Send /start
      msg = { from: { id: 123 }, chat: { id: 123 }, text: '/start' };
      await bot.handleMessage(msg);

      // History should be cleared
      expect(bot.getHistory()).toEqual([]);
    });
  });

  describe('Authorization', () => {
    it('should reject messages from unauthorized users', async () => {
      const msg = {
        from: { id: 999 }, // Wrong user
        chat: { id: 999 },
        text: 'Hello',
      };

      await bot.handleMessage(msg);

      expect(mockTelegram.sendMessage).toHaveBeenCalledWith(
        expect.anything(),
        expect.stringContaining('Unauthorized')
      );
      expect(mockOllama.chat).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle Ollama errors gracefully', async () => {
      mockOllama.chat.mockRejectedValue(new Error('Ollama timeout'));

      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: 'Hello',
      };

      await bot.handleMessage(msg);

      expect(mockTelegram.sendMessage).toHaveBeenCalledWith(
        expect.anything(),
        expect.stringContaining('Error')
      );
    });

    it('should handle Telegram API errors with retry', async () => {
      mockTelegram.sendMessage
        .mockRejectedValueOnce(new Error('429 Too Many Requests'))
        .mockResolvedValueOnce({});

      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: 'Hello',
      };

      await bot.handleMessage(msg);

      // Should retry and eventually succeed
      expect(mockTelegram.sendMessage).toHaveBeenCalledTimes(2);
    });
  });

  describe('Performance', () => {
    it('should handle tokens per second metric', async () => {
      mockOllama.chat.mockResolvedValue({
        message: { content: 'Response' },
        eval_count: 100,
        eval_duration: 1e9, // 1 second in nanoseconds
      });

      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: 'Hello',
      };

      const startTime = Date.now();
      await bot.handleMessage(msg);
      const duration = Date.now() - startTime;

      const metrics = bot.getLastMetrics();
      expect(metrics?.tokensPerSecond).toBeCloseTo(100, 0); // 100 tokens/sec
    });
  });
});
```

---

## Integration Testing

### Test File: `bot.integration.test.ts`

```typescript
import nock from 'nock';

describe('TelegramOllamaBot Integration', () => {
  let bot: TelegramOllamaBot;

  beforeEach(() => {
    // Real Telegram mock
    nock('https://api.telegram.org')
      .post('/botTEST_TOKEN/sendMessage')
      .reply(200, { ok: true, result: { message_id: 1 } });

    // Real Ollama mock
    nock('http://localhost:11434')
      .post('/api/chat')
      .reply(200, {
        model: 'llama2',
        message: {
          role: 'assistant',
          content: 'This is a test response',
        },
        done: true,
      });

    bot = new TelegramOllamaBot();
  });

  it('should process complete message flow', async () => {
    const message = {
      from: { id: 123, first_name: 'Test' },
      chat: { id: 123 },
      text: 'What is 2+2?',
    };

    await bot.handleMessage(message);

    // Verify Ollama was called
    expect(nock.isDone()).toBe(true);

    // Verify message is in history
    expect(bot.getHistory()).toContainEqual({
      role: 'user',
      content: 'What is 2+2?',
    });
  });

  it('should handle streaming responses', async () => {
    let callCount = 0;

    nock('http://localhost:11434')
      .post('/api/chat')
      .reply(() => {
        callCount++;
        return [
          200,
          [
            JSON.stringify({
              model: 'llama2',
              message: { role: 'assistant', content: '4' },
              done: false,
            }),
            JSON.stringify({
              model: 'llama2',
              message: { role: 'assistant', content: ' ' },
              done: false,
            }),
            JSON.stringify({
              model: 'llama2',
              message: { role: 'assistant', content: 'is' },
              done: false,
            }),
            JSON.stringify({
              model: 'llama2',
              message: { role: 'assistant', content: ' the answer' },
              done: true,
              eval_count: 10,
              eval_duration: 1e9,
            }),
          ].join('\n'),
        ];
      });

    const message = {
      from: { id: 123 },
      chat: { id: 123 },
      text: '2+2',
    };

    await bot.handleMessage(message);

    // Should have collected all tokens
    expect(bot.getHistory()[1].content).toBe('4 is the answer');
  });
});
```

---

## E2E Testing (Manual)

### Test Script: `test-e2e.sh`

```bash
#!/bin/bash

# Start bot in background
npx ts-node bot.ts &
BOT_PID=$!

# Give bot time to initialize
sleep 2

# Function to send test message
send_message() {
  local message=$1
  local expected=$2

  curl -s -X POST "https://api.telegram.org/botTEST_TOKEN/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
      \"chat_id\": $TEST_USER_ID,
      \"text\": \"$message\"
    }"

  # Wait for response
  sleep 2

  # Check if response contains expected text
  if grep -q "$expected" last_response.log; then
    echo "✅ Test passed: $message"
    return 0
  else
    echo "❌ Test failed: $message"
    cat last_response.log
    return 1
  fi
}

# Run tests
echo "Starting E2E tests..."

send_message "Hello" "Hello"
send_message "What is 2+2?" "4"
send_message "What was that about?" "math\|2\+2\|arithmetic"
send_message "/start" "reset\|cleared\|started"

# Cleanup
kill $BOT_PID

echo "✅ E2E tests complete"
```

---

## Stress Testing

### Test File: `bot.stress.test.ts`

```typescript
describe('Stress Testing', () => {
  it('should handle 100 sequential messages', async () => {
    const bot = new TelegramOllamaBot();
    const msg = {
      from: { id: 123 },
      chat: { id: 123 },
      text: 'Test message',
    };

    const startTime = Date.now();

    for (let i = 0; i < 100; i++) {
      await bot.handleMessage(msg);
    }

    const duration = Date.now() - startTime;

    console.log(`100 messages processed in ${duration}ms`);
    console.log(`Average: ${duration / 100}ms per message`);

    expect(duration).toBeLessThan(60000); // Should complete in < 60 seconds
  });

  it('should not leak memory over time', async () => {
    const bot = new TelegramOllamaBot();

    const initialMemory = process.memoryUsage().heapUsed;

    for (let i = 0; i < 1000; i++) {
      const msg = {
        from: { id: 123 },
        chat: { id: 123 },
        text: `Message ${i}`,
      };

      await bot.handleMessage(msg);
    }

    const finalMemory = process.memoryUsage().heapUsed;
    const increase = finalMemory - initialMemory;

    console.log(`Memory increase: ${(increase / 1024 / 1024).toFixed(2)}MB`);

    // Should not increase more than 50MB
    expect(increase).toBeLessThan(50 * 1024 * 1024);
  });

  it('should handle model unload gracefully', async () => {
    const bot = new TelegramOllamaBot();

    // Simulate Ollama model unloading
    mockOllama.chat.mockRejectedValue(
      new Error('model not found - try pulling it first')
    );

    const msg = {
      from: { id: 123 },
      chat: { id: 123 },
      text: 'Test',
    };

    await expect(bot.handleMessage(msg)).rejects.toThrow('model not found');

    // Bot should recover and try to reload
    mockOllama.chat.mockResolvedValue({
      message: { content: 'Recovered' },
    });

    await bot.handleMessage(msg);
    expect(mockOllama.chat).toHaveBeenCalled();
  });
});
```

---

## Debugging Checklist

When bot stops responding, check in order:

### 1. Ollama Health
```bash
# Is Ollama running?
curl http://localhost:11434/api/version

# Is model loaded?
curl http://localhost:11434/api/ps

# Load model if needed
ollama pull llama2
```

### 2. Telegram Connection
```bash
# Is token valid?
curl https://api.telegram.org/botTOKEN/getMe

# Can you send a message?
curl -X POST https://api.telegram.org/botTOKEN/sendMessage \
  -H "Content-Type: application/json" \
  -d '{"chat_id": YOUR_USER_ID, "text": "Test"}'
```

### 3. Bot Logs
```bash
# Enable debug logging
DEBUG=* npx ts-node bot.ts

# Check for errors
tail -f bot.log | grep ERROR
```

### 4. Network Issues
```bash
# Test Ollama connection
timeout 5 curl -v http://localhost:11434/api/version

# Test Telegram connection
timeout 5 curl -v https://api.telegram.org/botTOKEN/getMe

# Check firewall
netstat -tlnp | grep 11434
```

---

## Test Coverage Report

After running tests, generate coverage:

```bash
npm test -- --coverage
```

Aim for:
- **Line coverage**: > 80%
- **Branch coverage**: > 75%
- **Function coverage**: > 85%

### Example Coverage Report:

```
File                     | Coverage
-----------------------|----------
bot.ts                  | 92%
message-handler.ts      | 87%
ollama-client.ts        | 94%
telegram-api.ts         | 85%
conversation-memory.ts  | 91%
-----------------------|----------
Total                   | 90%
```

---

## CI/CD Integration

### GitHub Actions: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Pull Ollama model
        run: ollama pull llama2

      - name: Run unit tests
        run: npm test -- --coverage

      - name: Run integration tests
        run: npm run test:integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

---

## Test Commands

```bash
# Run all tests
npm test

# Run specific test file
npm test -- bot.test.ts

# Run with coverage
npm test -- --coverage

# Run in watch mode (auto-rerun on changes)
npm test -- --watch

# Run integration tests only
npm test -- --testPathPattern=integration

# Run with verbose output
npm test -- --verbose

# Generate HTML coverage report
npm test -- --coverage --coverageReporters=html
```

---

## Known Issues & Workarounds

### Issue 1: "Model not found" in production
**Root cause**: Ollama unloads model after 5 minutes of inactivity  
**Workaround**: Periodically send keep-alive message to Ollama
```typescript
setInterval(() => {
  ollama.chat({ model, messages: [], stream: false });
}, 4 * 60 * 1000); // Every 4 minutes
```

### Issue 2: Memory leaks in streaming
**Root cause**: Not properly closing fetch streams  
**Workaround**: Always call `reader.releaseLock()`

### Issue 3: Race condition on rapid button clicks
**Root cause**: No message queue, multiple handlers fire simultaneously  
**Workaround**: Use mutex/semaphore (see main guide)

---

**Last Updated**: February 2026
