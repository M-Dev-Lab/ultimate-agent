#!/usr/bin/env node

import { Agent } from './core/agent.js';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.join(process.cwd(), '.env') });

async function main() {
  console.log('🚀 Starting Ultimate Coding Agent (Telegram Mode)...');

  const agent = new Agent();

  try {
    await agent.initialize();
    console.log('✅ Agent initialized successfully');
    console.log('📱 Telegram bot is listening for commands...');
    console.log('🎉 Ready to build projects!');
  } catch (error: any) {
    console.error('❌ Failed to start agent:', error.message);
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }

  gracefulShutdown(agent);
}

function gracefulShutdown(agent: Agent) {
  const shutdownHandler = async (signal: string) => {
    console.log(`\n📢 Received ${signal}, shutting down gracefully...`);
    await agent.shutdown();
    process.exit(0);
  };

  process.on('SIGINT', () => shutdownHandler('SIGINT'));
  process.on('SIGTERM', () => shutdownHandler('SIGTERM'));

  process.on('uncaughtException', (error) => {
    console.error('❌ Uncaught Exception:', error);
    process.exit(1);
  });

  process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
  });
}

main();
