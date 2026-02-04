/**
 * Telegram + Ollama Local LLM Integration
 * Minimal Working Example (~200 lines)
 * 
 * USAGE:
 * 1. Start Ollama: ollama serve
 * 2. Pull a model: ollama pull llama2
 * 3. Install deps: npm install node-telegram-bot-api axios
 * 4. Run: TELEGRAM_TOKEN=xxx USER_ID=yyy npx ts-node telegram-ollama-minimal.ts
 * 
 * OR for Deno:
 * deno run --allow-net --allow-env telegram-ollama-minimal.ts
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
  TELEGRAM_TOKEN: process.env.TELEGRAM_TOKEN || '',
  OLLAMA_URL: process.env.OLLAMA_URL || 'http://localhost:11434',
  ADMIN_USER_ID: parseInt(process.env.USER_ID || '0'),
  MODEL: process.env.MODEL || 'llama2',
  MAX_HISTORY: 10, // Keep last N messages in memory
};

// ============================================================================
// TYPES
// ============================================================================

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface OllamaResponse {
  model: string;
  message: {
    role: 'assistant';
    content: string;
  };
  done: boolean;
  total_duration?: number;
  eval_count?: number;
  eval_duration?: number;
}

interface Update {
  update_id: number;
  message?: {
    message_id: number;
    from: {id: number; first_name: string};
    chat: {id: number};
    text?: string;
  };
  callback_query?: {
    id: string;
    from: {id: number};
    data: string;
    message?: {chat: {id: number}; message_id: number};
  };
}

// ============================================================================
// CORE BOT CLASS
// ============================================================================

class TelegramOllamaBot {
  private conversationHistory: Message[] = [];
  private isProcessing = false;
  private lastUpdateId = 0;

  async start(): Promise<void> {
    console.log(`🤖 Bot starting (user: ${CONFIG.ADMIN_USER_ID})`);
    console.log(`📚 Model: ${CONFIG.MODEL}`);
    console.log(`🌐 Ollama URL: ${CONFIG.OLLAMA_URL}`);

    // Check health
    const isHealthy = await this.checkHealth();
    if (!isHealthy) {
      console.error('❌ Ollama is not responding. Make sure to run: ollama serve');
      process.exit(1);
    }

    // Start polling
    console.log('✅ Connected to Ollama');
    console.log('⏳ Waiting for messages...\n');
    this.poll();
  }

  // ========================================================================
  // POLLING & EVENT HANDLING
  // ========================================================================

  private async poll(): Promise<void> {
    while (true) {
      try {
        const updates = await this.getUpdates();

        for (const update of updates) {
          if (update.message?.text) {
            await this.handleMessage(update.message);
          } else if (update.callback_query) {
            await this.handleCallback(update.callback_query);
          }
        }

        // Update offset for next poll
        if (updates.length > 0) {
          this.lastUpdateId = updates[updates.length - 1].update_id + 1;
        }

        // Small delay to avoid CPU spinning
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (error) {
        console.error('Poll error:', (error as Error).message);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }

  private async getUpdates(): Promise<Update[]> {
    const response = await fetch(
      `${CONFIG.OLLAMA_URL.replace('11434', '6379')}/bot${CONFIG.TELEGRAM_TOKEN}/getUpdates?offset=${this.lastUpdateId}&timeout=10`,
      {method: 'GET'}
    );

    if (!response.ok) {
      throw new Error(`Telegram API error: ${response.statusText}`);
    }

    const data = await response.json() as {ok: boolean; result: Update[]};
    return data.result || [];
  }

  // ========================================================================
  // MESSAGE HANDLING
  // ========================================================================

  private async handleMessage(msg: Update['message']): Promise<void> {
    if (!msg) return;

    // Check if user is authorized
    if (msg.from.id !== CONFIG.ADMIN_USER_ID) {
      await this.sendMessage(msg.chat.id, '❌ Unauthorized');
      return;
    }

    // Prevent concurrent processing
    if (this.isProcessing) {
      console.log('⏳ Already processing, queueing next message');
      return;
    }

    this.isProcessing = true;

    try {
      const text = msg.text || '';

      // Handle special commands
      if (text === '/start') {
        this.conversationHistory = [];
        await this.sendMessage(msg.chat.id, '🔄 Conversation reset');
        this.isProcessing = false;
        return;
      }

      if (text === '/history') {
        const summary = this.conversationHistory
          .map((m, i) => `${i}. ${m.role}: ${m.content.substring(0, 50)}...`)
          .join('\n');
        await this.sendMessage(msg.chat.id, `📝 History:\n${summary}`);
        this.isProcessing = false;
        return;
      }

      // Show typing indicator
      await this.sendChatAction(msg.chat.id, 'typing');

      // Add user message to history
      this.conversationHistory.push({
        role: 'user',
        content: text,
      });

      console.log(`👤 User: "${text}"`);

      // Get response from Ollama
      const response = await this.callOllama(this.conversationHistory);

      // Add assistant response to history
      this.conversationHistory.push({
        role: 'assistant',
        content: response,
      });

      // Prune old messages if history gets too long
      if (this.conversationHistory.length > CONFIG.MAX_HISTORY) {
        this.conversationHistory = this.conversationHistory.slice(-CONFIG.MAX_HISTORY);
      }

      // Send response to Telegram
      await this.sendMessage(msg.chat.id, response);
      console.log(`🤖 Assistant: "${response.substring(0, 100)}..."\n`);
    } catch (error) {
      await this.sendMessage(msg.chat.id, `❌ Error: ${(error as Error).message}`);
      console.error('Message handling error:', (error as Error).message);
    } finally {
      this.isProcessing = false;
    }
  }

  private async handleCallback(query: Update['callback_query']): Promise<void> {
    if (!query) return;

    // Check authorization
    if (query.from.id !== CONFIG.ADMIN_USER_ID) return;

    // Acknowledge immediately
    await this.answerCallbackQuery(query.id);

    console.log(`📌 Button clicked: ${query.data}`);

    // Process action
    const userMessage = `[Button clicked: ${query.data}]`;
    this.conversationHistory.push({role: 'user', content: userMessage});

    const response = await this.callOllama(this.conversationHistory);
    this.conversationHistory.push({role: 'assistant', content: response});

    if (query.message) {
      await this.sendMessage(query.message.chat.id, response);
    }
  }

  // ========================================================================
  // OLLAMA INTEGRATION
  // ========================================================================

  private async callOllama(messages: Message[]): Promise<string> {
    const response = await fetch(`${CONFIG.OLLAMA_URL}/api/chat`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        model: CONFIG.MODEL,
        messages,
        stream: false,
        options: {
          temperature: 0.7,
          top_k: 40,
          top_p: 0.9,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama error: ${response.statusText}`);
    }

    const data = await response.json() as OllamaResponse;
    return data.message.content.trim();
  }

  private async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${CONFIG.OLLAMA_URL}/api/version`);
      return response.ok;
    } catch {
      return false;
    }
  }

  // ========================================================================
  // TELEGRAM API METHODS
  // ========================================================================

  private async sendMessage(chatId: number, text: string): Promise<void> {
    const response = await fetch(
      `https://api.telegram.org/bot${CONFIG.TELEGRAM_TOKEN}/sendMessage`,
      {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chat_id: chatId, text}),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`);
    }
  }

  private async sendChatAction(chatId: number, action: string): Promise<void> {
    await fetch(
      `https://api.telegram.org/bot${CONFIG.TELEGRAM_TOKEN}/sendChatAction`,
      {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chat_id: chatId, action}),
      }
    );
  }

  private async answerCallbackQuery(queryId: string): Promise<void> {
    await fetch(
      `https://api.telegram.org/bot${CONFIG.TELEGRAM_TOKEN}/answerCallbackQuery`,
      {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({callback_query_id: queryId}),
      }
    );
  }
}

// ============================================================================
// MAIN
// ============================================================================

async function main(): Promise<void> {
  // Validate config
  if (!CONFIG.TELEGRAM_TOKEN) {
    console.error('❌ TELEGRAM_TOKEN environment variable required');
    process.exit(1);
  }

  if (CONFIG.ADMIN_USER_ID === 0) {
    console.error('❌ USER_ID environment variable required');
    process.exit(1);
  }

  const bot = new TelegramOllamaBot();
  await bot.start();
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
