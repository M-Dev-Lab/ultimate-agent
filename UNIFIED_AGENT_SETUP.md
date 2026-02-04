# 🤖 Unified Python Agent Setup (Feb 4, 2026)

**Status**: ✅ UNIFIED | **One Single Agent** | **Python FastAPI + Telegram**

---

## What Changed

Previously you had **duplicate agents**:
- ❌ Node.js Telegram bot (src/telegram.ts)
- ❌ Python FastAPI backend (python-agent/)
- **Result**: Two bots responding to same Telegram commands = chaos

**Now Fixed**:
- ✅ **Single Python FastAPI Agent** at port 8000
- ✅ **Python Telegram Bot** (polling mode) integrated in FastAPI startup
- ✅ **Node.js disabled** to prevent conflicts
- ✅ **Latest dependencies** (Feb 2026)
  - python-telegram-bot v22.6 (latest)
  - FastAPI 0.115.6
  - All packages updated

---

## Quick Start (5 minutes)

### 1. Enter Python Environment
```bash
cd /home/zeds/Desktop/ultimate-agent/python-agent
source venv/bin/activate
```

### 2. Verify Configuration
```bash
# Check Python agent has USE_PYTHON_TELEGRAM=true
grep "USE_PYTHON_TELEGRAM" .env
# Should output: USE_PYTHON_TELEGRAM=true

# Check root .env has empty TELEGRAM_BOT_TOKEN (Node.js disabled)
grep "TELEGRAM_BOT_TOKEN=" ../.env
# Should output: TELEGRAM_BOT_TOKEN=  (empty)
```

### 3. Start the Agent
```bash
# Single command to start API + Telegram bot
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**You should see**:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
✅ Python Telegram bot initialized
🤖 Initializing Telegram bot...
📱 Telegram bot started
🚀 Sending startup notification to admin...
✅ Startup notification sent to admin
INFO:     Application startup complete.
```

### 4. Test in Telegram
Send your admin ID a test message:
```bash
# In Telegram chat with bot:
/start
```

**Expected**: ✅ Welcome message from single Python agent

---

## Architecture

### Before (Broken)
```
Telegram Chat
    ↓
  ┌─────────────────────┐
  │  Node.js Bot        │  ❌ Running
  │  (src/telegram.ts)  │
  └─────────────────────┘
    ↓
  ┌─────────────────────┐
  │  Python Bot         │  ❌ Also Running
  │  (telegram_bot.py)  │
  └─────────────────────┘
    ↓
  USER CONFUSION: Two bots responding!
```

### After (Fixed)
```
Telegram Chat
    ↓
  ┌────────────────────────────────┐
  │  Python FastAPI (port 8000)    │ ✅ Single Agent
  │  + Telegram Bot (polling)      │
  │                                │
  │  app/main.py                   │
  │  → integrations/telegram_bot.py│
  └────────────────────────────────┘
    ↓
  Admin receives messages from ONE source
```

---

## Configuration Reference

### Python Agent (.env)
| Setting | Value | Purpose |
|---------|-------|---------|
| `USE_PYTHON_TELEGRAM` | `true` | Enable Python Telegram bot at startup |
| `TELEGRAM_BOT_TOKEN` | YOUR_TOKEN | Telegram bot API token |
| `ADMIN_TELEGRAM_IDS` | [YOUR_ID] | Admin user ID(s) |
| `OLLAMA_HOST` | http://localhost:11434 | Local Ollama instance |
| `OLLAMA_MODEL` | qwen2.5-coder:7b-instruct-q5_K_M | AI model |
| `DATABASE_URL` | sqlite:///./data/agent.db | Local database |

### Root .env (Disabled Node Bot)
| Setting | Value | Purpose |
|---------|-------|---------|
| `TELEGRAM_BOT_TOKEN` | (empty) | ✅ Node.js disabled |
| `ADMIN_TELEGRAM_ID` | YOUR_ID | For reference only |

---

## Running the Agent

### Option 1: Development (Recommended for Testing)
```bash
cd /home/zeds/Desktop/ultimate-agent/python-agent
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Features**: Auto-reload on code changes, verbose logging

### Option 2: Systemd Service (Production)
```bash
# Copy systemd service
sudo cp systemd/ultimate-agent-python.service /etc/systemd/system/

# Enable auto-start
sudo systemctl daemon-reload
sudo systemctl enable ultimate-agent-python.service

# Start service
sudo systemctl start ultimate-agent-python.service

# Check status
sudo systemctl status ultimate-agent-python.service

# View logs
sudo journalctl -u ultimate-agent-python.service -f
```

### Option 3: Docker (Optional)
```bash
docker-compose up -d

# View logs
docker-compose logs -f python-agent
```

---

## Troubleshooting

### No Telegram Response
1. **Check token is valid**:
   ```bash
   python -c "from telegram import Bot; Bot('YOUR_TOKEN').get_me()"
   ```

2. **Check bot is running**:
   ```bash
   ps aux | grep uvicorn
   ```

3. **Check logs**:
   ```bash
   tail -100 python-agent/logs/app.log | grep -i telegram
   ```

### API Not Starting
1. **Port 8000 in use**:
   ```bash
   lsof -i :8000  # Find process
   kill -9 PID
   ```

2. **Missing dependencies**:
   ```bash
   cd python-agent
   source venv/bin/activate
   pip install -r requirements.txt --upgrade
   ```

3. **Database error**:
   ```bash
   rm -rf python-agent/data/agent.db  # Reset database
   python -m pytest tests/ -v  # Run tests
   ```

### Duplicate Messages
1. **Node.js bot still running**:
   ```bash
   pkill -f "node src/telegram" || true
   pkill -f "npm start" || true
   ps aux | grep node  # Verify stopped
   ```

2. **Check root .env**:
   ```bash
   grep "TELEGRAM_BOT_TOKEN=" .env
   # Should be empty!
   ```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/api/v1/builds` | POST | Create build |
| `/api/v1/code/analyze` | POST | Analyze code |
| `/api/v1/code/generate` | POST | Generate code |
| `/docs` | GET | Interactive API docs (Swagger) |

**Example**:
```bash
curl http://127.0.0.1:8000/health | jq .
```

---

## Testing

### Unit Tests (All Passing ✅)
```bash
cd python-agent
source venv/bin/activate
python -m pytest tests/test_local_env.py -v
# Expected: 28 passed, 2 warnings in 1.13s
```

### Telegram Bot Test
```bash
# Send message to bot in Telegram
/start

# Check logs
tail -50 python-agent/logs/app.log | grep -i "received\|telegram"
```

### API Test
```bash
# Health check
curl http://127.0.0.1:8000/health | jq .

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-04T...",
#   "version": "3.0.0",
#   "environment": "development"
# }
```

---

## Key Files Changed

1. **python-agent/.env**
   - Added: `USE_PYTHON_TELEGRAM=true`
   - Enabled Python Telegram bot startup

2. **python-agent/app/core/config.py**
   - Added: `use_python_telegram` setting

3. **python-agent/app/main.py**
   - Added: Conditional Telegram bot startup
   - Added: Imports for telegram functions
   - Moved: Telegram init to startup event

4. **.env (root)**
   - Cleared: `TELEGRAM_BOT_TOKEN` (empty)
   - Disabled: Node.js Telegram bot

5. **python-agent/requirements.txt**
   - Updated: All dependencies to Feb 2026 versions
   - python-telegram-bot v22.6 (latest)

6. **systemd/ultimate-agent-python.service** (NEW)
   - Systemd unit for auto-start in production

---

## Commands in Telegram

Send these commands to the bot:

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot, show menu |
| `/help` | Show all commands |
| `/build [name]` | Create a new project |
| `/skill [name]` | Use a skill |
| `/status` | System status |
| `/health` | Health check |
| `/file [op] [path]` | File operations |
| `/post [platform] [text]` | Social posting |
| `/open [url]` | Open URL |

---

## Next Steps

1. ✅ **Verify Bot is Running**
   - Send `/start` in Telegram
   - Should get ONE response from Python agent

2. ✅ **Check Logs**
   ```bash
   tail -f python-agent/logs/app.log
   ```

3. ✅ **Use Dashboard** (Optional)
   - http://localhost:3000 (Node dashboard, if enabled)
   - Or use Telegram for all operations

4. ✅ **Schedule as Service** (Optional, Production)
   ```bash
   sudo systemctl enable ultimate-agent-python.service
   ```

---

## Support

### Common Issues
- **Bot not responding**: Check Telegram token in `python-agent/.env`
- **Port 8000 busy**: Kill existing process with `pkill -f uvicorn`
- **Tests failing**: Update dependencies with `pip install -r requirements.txt --upgrade`

### Debug Mode
```bash
# Run with verbose logging
DEBUG=True uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

### Contact
All system logs in: `python-agent/logs/app.log`

---

**Status**: ✅ Unified Agent Ready | **Last Updated**: February 4, 2026
