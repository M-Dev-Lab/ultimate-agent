"""
LOCAL ENVIRONMENT SETUP GUIDE
Ultimate Coding Agent v3.0 with Ollama Cloud Integration

This guide explains how to set up and run the project locally using:
- SQLite for local development
- Redis for caching/tasks
- Ollama Cloud (qwen2.5-coder:480b) via SSH tunnel
- Z-Desktop for remote Ollama service
"""

# ==================== PREREQUISITES ====================

## System Requirements
- Linux/Mac/Windows with WSL
- Python 3.11+
- Git
- Redis (for Celery task queue)
- SSH access to Z-Desktop (with ed25519 key)

## Check Your Setup
```bash
# Verify Python
python3 --version  # Should be 3.11+

# Verify Git
git --version

# Check SSH key
ls -la ~/.ssh/id_ed25519
# Should show your SSH key
```

---

# ==================== QUICK START (5 MINUTES) ====================

## 1. Clone and Setup
```bash
cd ~/Desktop/ultimate-agent/python-agent

# Run setup script (automated)
chmod +x setup-local-env.sh
./setup-local-env.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data/{chroma,workspaces,memory} logs
```

## 2. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit .env with:
nano .env
```

**Critical settings to update:**
```env
# Generate new JWT secret
JWT_SECRET=your-secure-key-here

# Your Ollama Cloud API key
OLLAMA_API_KEY=your_api_key_here

# SSH to Z-Desktop
SSH_KEY_PATH=/home/zeds/.ssh/id_ed25519
SSH_HOST=z-desktop
SSH_USER=zeds
```

## 3. Start Services
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: SSH Tunnel to Z-Desktop (Ollama Cloud)
ssh -L 11434:localhost:11434 -i ~/.ssh/id_ed25519 zeds@z-desktop

# Terminal 3: FastAPI Server
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 4: Celery Worker (optional)
celery -A app.tasks worker --loglevel=info
```

## 4. Verify Setup
```bash
# Test API
curl http://localhost:8000/api/health/

# Access Swagger UI
open http://localhost:8000/docs

# Test Ollama connection
curl -H "Authorization: Bearer $OLLAMA_API_KEY" \
  https://ollama.z-desktop.local:11434/api/tags
```

---

# ==================== DETAILED SETUP ====================

## Step 1: SSH Key Setup

Your SSH key for Z-Desktop:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICmbrajl4ntnmy/r2coBXGV9ADhWqndC89/2+BnJAdPM
```

**Setup:**
```bash
# Ensure SSH key is in place
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add to ssh config for easy access
cat >> ~/.ssh/config << 'EOF'
Host z-desktop
    HostName z-desktop.local  # or IP address
    User zeds
    IdentityFile ~/.ssh/id_ed25519
    Port 22
EOF

# Test SSH connection
ssh -v z-desktop "echo 'SSH connection successful'"
```

## Step 2: SSH Tunnel for Ollama Cloud

Ollama Cloud is running on Z-Desktop at `localhost:11434`. To access it:

```bash
# Option 1: Simple port forwarding
ssh -L 11434:localhost:11434 z-desktop

# Option 2: Keep tunnel running in background
ssh -L 11434:localhost:11434 -N -f z-desktop

# Option 3: With key passphrase prompt
ssh -L 11434:localhost:11434 -i ~/.ssh/id_ed25519 zeds@z-desktop
```

**Verify tunnel:**
```bash
curl -s http://localhost:11434/api/tags | jq .
# Should show available models including qwen2.5-coder:480b
```

## Step 3: Database Setup

### SQLite (Local Database)
```env
# In .env
DATABASE_URL=sqlite:///./data/agent.db
```

```bash
# Initialize database
python3 << 'PYTHON'
import asyncio
from app.db.session import init_db

asyncio.run(init_db())
print("✓ Database initialized")
PYTHON
```

## Step 4: Redis Setup

```bash
# Install Redis
brew install redis  # macOS
# or apt-get install redis-server  # Linux

# Start Redis
redis-server

# Verify
redis-cli ping
# Should return: PONG
```

## Step 5: Ollama Cloud Configuration

```env
# In .env
OLLAMA_HOST=https://ollama.z-desktop.local:11434
OLLAMA_MODEL=qwen2.5-coder:480b
OLLAMA_API_KEY=your_ollama_cloud_api_key
OLLAMA_TIMEOUT=300
```

**First time setup:**
```bash
# Start SSH tunnel in one terminal
ssh -L 11434:localhost:11434 z-desktop

# In another terminal, test connection
python3 << 'PYTHON'
import httpx
import os

api_key = os.getenv("OLLAMA_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

# Test connection
response = httpx.get(
    "http://localhost:11434/api/tags",
    headers=headers,
    timeout=10
)
print(f"Status: {response.status_code}")
print(f"Available models: {response.json()}")
PYTHON
```

## Step 6: Environment Variables

**Full .env template:**
```env
# Application
APP_NAME="Ultimate Coding Agent v3.0"
DEBUG=True
ENVIRONMENT=development

# Security
JWT_SECRET=your-minimum-32-character-secret-key-here

# Database
DATABASE_URL=sqlite:///./data/agent.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama Cloud
OLLAMA_HOST=https://ollama.z-desktop.local:11434
OLLAMA_MODEL=qwen2.5-coder:480b
OLLAMA_API_KEY=your_api_key_here
OLLAMA_TIMEOUT=300

# SSH for Z-Desktop
SSH_KEY_PATH=/home/zeds/.ssh/id_ed25519
SSH_HOST=z-desktop
SSH_USER=zeds

# Paths
DATA_DIR=./data
LOGS_DIR=./logs

# Features
ENABLE_AGENT_WORKFLOW=True
ENABLE_VECTOR_SEARCH=True
ENABLE_METRICS_EXPORT=True
```

---

# ==================== RUNNING THE APPLICATION ====================

## Terminal 1: Redis
```bash
redis-server
# Output: Ready to accept connections
```

## Terminal 2: SSH Tunnel
```bash
ssh -L 11434:localhost:11434 z-desktop
# Keep this running - it provides Ollama Cloud access
```

## Terminal 3: FastAPI Server
```bash
cd ~/Desktop/ultimate-agent/python-agent
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Output:
# Uvicorn running on http://127.0.0.1:8000
```

## Terminal 4: Celery Worker (Optional)
```bash
source venv/bin/activate
celery -A app.tasks worker --loglevel=info

# Output:
# [*] Ready to accept tasks
```

---

# ==================== TESTING THE SETUP ====================

## Health Check
```bash
# Basic health
curl http://localhost:8000/api/health/

# Response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-03T10:30:00Z",
#   "health_score": 0.95
# }
```

## Swagger UI
```
Open browser: http://localhost:8000/docs
```

## Create a Build
```bash
# Get JWT token first (if needed)
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Create build
curl -X POST http://localhost:8000/api/build/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test_project",
    "requirements": "Create a simple calculator"
  }'
```

## Test Ollama Connection
```bash
python3 << 'PYTHON'
import httpx
import os

api_key = os.getenv("OLLAMA_API_KEY", "test_key")
headers = {"Authorization": f"Bearer {api_key}"}

try:
    response = httpx.get(
        "http://localhost:11434/api/tags",
        headers=headers,
        timeout=5
    )
    print(f"✓ Ollama connection: OK")
    models = response.json().get("models", [])
    print(f"  Available models: {len(models)}")
    for model in models:
        print(f"    - {model.get('name')}")
except Exception as e:
    print(f"✗ Ollama connection failed: {e}")
    print("  Ensure SSH tunnel is active: ssh -L 11434:localhost:11434 z-desktop")
PYTHON
```

---

# ==================== TROUBLESHOOTING ====================

## Connection Issues

### Redis not found
```bash
# Install
brew install redis
# Start
redis-server
```

### SSH tunnel connection refused
```bash
# Check SSH connection first
ssh -v z-desktop "uname -a"

# Try with explicit key
ssh -L 11434:localhost:11434 -i ~/.ssh/id_ed25519 zeds@z-desktop
```

### Ollama Cloud unreachable
```bash
# Check tunnel
nc -zv localhost 11434

# Check Ollama API directly (from Z-Desktop)
ssh z-desktop "curl localhost:11434/api/tags"
```

### Database locked (SQLite)
```bash
# Remove lock file
rm ./data/agent.db-*

# Reinitialize
python3 -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"
```

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Use different port
uvicorn app.main:app --port 8001
```

---

# ==================== DEVELOPMENT TIPS ====================

## Hot Reload
FastAPI dev mode watches for file changes:
```bash
uvicorn app.main:app --reload
```

## Database Reset
```bash
# For SQLite
rm ./data/agent.db
python3 -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"
```

## View Logs
```bash
# API logs
tail -f logs/api.log

# Celery logs
celery -A app.tasks worker --loglevel=debug
```

## Database Inspection
```bash
# SQLite (if using SQLite)
sqlite3 ./data/agent.db

# List tables
.tables

# Query builds
SELECT id, project_name, status FROM builds LIMIT 5;
```

## Performance Monitoring
```bash
# Prometheus metrics
curl http://localhost:8000/metrics
```

---

# ==================== NEXT STEPS ====================

1. **✓ Environment Setup** (you are here)
2. **→ Run Tests** 
   ```bash
   pytest tests/ -v
   ```
3. **→ Create Your First Build**
   Use Swagger UI at http://localhost:8000/docs
4. **→ Configure Telegram Bot** (optional)
   Add TELEGRAM_BOT_TOKEN to .env

---

**Questions or issues?** Check logs in `./logs/` or review `.env` configuration.
