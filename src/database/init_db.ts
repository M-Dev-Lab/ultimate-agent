import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';

// Convert import.meta.url to __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, '../../data/db/interactions.db');

async function initializeDatabase() {
  try {
    // Open database
    const db = await open({
      filename: dbPath,
      driver: sqlite3.Database
    });

    // Create interactions table (keep existing + add new)
    await db.exec(`
      CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        command TEXT NOT NULL,
        user_input TEXT,
        agent_response TEXT,
        success BOOLEAN,
        rating INTEGER,
        model_used TEXT,
        execution_time FLOAT,
        tags TEXT,
        memory_updated BOOLEAN DEFAULT FALSE
      );
    `);

    // Create skills table
    await db.exec(`
      CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT UNIQUE NOT NULL,
        skill_slug TEXT UNIQUE NOT NULL,
        category TEXT,
        description TEXT,
        installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_used DATETIME,
        use_count INTEGER DEFAULT 0,
        success_rate FLOAT,
        clawhub_version TEXT
      );
    `);

    // Create heartbeats table
    await db.exec(`
      CREATE TABLE IF NOT EXISTS heartbeats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT, -- 'OK' or 'ALERT'
        message TEXT,
        action_taken TEXT
      );
    `);

    // Create proactive_actions table
    await db.exec(`
      CREATE TABLE IF NOT EXISTS proactive_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        trigger TEXT, -- 'heartbeat', 'cron', 'event'
        action TEXT,
        outcome TEXT,
        user_approval TEXT -- 'pending', 'approved', 'rejected'
      );
    `);

    console.log('✅ Database initialized successfully');
    await db.close();
  } catch (error) {
    console.error('❌ Failed to initialize database:', error);
    process.exit(1);
  }
}

// Run initialization if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  initializeDatabase();
}

export { initializeDatabase };