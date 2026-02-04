# 🤖 Ultimate Agent - Unified Python Edition

**The all-in-one AI agent that controls your Linux machine via Telegram.**

Ultimate Agent is a production-ready, high-performance Python application that bridges the gap between powerful Large Language Models (LLMs) and local system operations. Built on FastAPI and `python-telegram-bot`, it features advanced error handling, persistent memory, and a comprehensive suite of productive skills.

---

## 🏗️ Architecture

Ultimate Agent has been consolidated from separate Node.js and Python implementations into a single, unified Python engine.

```mermaid
graph TD
    User([Telegram User]) <--> Bot[Telegram Bot Interface]
    Bot <--> Bridge[Agent Handler]
    
    subgraph Core_Engine [Unified Python Engine]
        Bridge <--> Memory[Memory Manager]
        Bridge <--> Router[Skill Router]
        Bridge <--> ErrorH[Error Handler]
        Bridge <--> Analytics[Analytics Tracker]
    end
    
    Router --> Skills{Skill Registry}
    Skills --> PM[Project Manager]
    Skills --> SP[Social Poster]
    Skills --> TS[Task Scheduler]
    Skills --> SC[System Controller]
    Skills --> FM[File Manager]
    Skills --> BC[Browser Controller]
    
    Core_Engine <--> DB[(SQLAlchemy DB)]
    Core_Engine <--> AI[Ollama / Cloud LLM]
```mermaid
graph TD
    User([Telegram User]) <--> Bot[Telegram Bot Interface]
    Bot <--> Bridge[Agent Handler]
    
    subgraph Core_Engine [Unified Python Engine]
        Bridge <--> Memory[Memory Manager]
        Bridge <--> Router[Skill Router]
        Bridge <--> ErrorH[Error Handler]
        Bridge <--> Analytics[Analytics Tracker]
    end
    
    Router --> Skills{Skill Registry}
    Skills --> PM[Project Manager]
    Skills --> SP[Social Poster]
    Skills --> TS[Task Scheduler]
    Skills --> SC[System Controller]
    Skills --> FM[File Manager]
    Skills --> BC[Browser Controller]
    
    Core_Engine <--> DB[(SQLAlchemy DB)]
    Core_Engine <--> Vector[(Vector DB / Chroma)]
    Core_Engine <--> AI[Ollama / Cloud LLM]
```

---

## 🔒 Security Hardening

- **Secure Sandbox**: Command execution is restricted to a whitelist and isolated from sensitive environment variables.
- **JWT & RBAC**: Enterprise-grade authentication with Role-Based Access Control.
- **Input Validation**: Multi-layer validation using Pydantic models to prevent injection attacks.
- **Circuit Breaker**: Isolates failing services to maintain system stability.

### 🧠 Advanced Memory Management
- **Context Awareness**: Retains conversation history with smart context window management.
- **SOUL Integration**: Personality and behavioral rules defined in `SOUL.md`.
- **Persistent Sessions**: Workflow states are saved to the database, allowing wizards to continue after restarts.

### 🛡️ Resilient Execution
- **Circuit Breaker Pattern**: Prevents cascading failures by detecting and isolating recurring errors.
- **Exponential Backoff**: Automatic retries for network and AI service interruptions.
- **Granular Error Handling**: Detailed categorization and user-friendly error messages.

### 🎯 Intelligent Routing
- **Intent Detection**: Automatically determines the best skill to handle user requests using pattern matching and keyword analysis.
- **Skill Registry**: A pluggable system for adding and managing specialized AI capabilities.

### 📊 Real-time Monitoring
- **Analytics Tracker**: Monitors message volume, response times, and skill success rates.
- **Health Dashboard**: Provides system status and performance metrics via API and Telegram.

### 🧙 Interactive Wizards
- **Project Wizard**: Multi-step guide for creating new software projects.
- **Social Wizard**: Optimize and post content to Twitter, LinkedIn, and more.
- **Schedule Wizard**: Set reminders and tasks with priority levels.
- **Learn Wizard**: Autonomous mode for reading documentation and updating internal knowledge.

---

## 🛠️ Performance Skills

| Skill | Capabilities |
|-------|--------------|
| **Project Manager** | Generate codebases, build APIs, and manage repositories. |
| **Social Poster** | Content optimization and automated browser-based posting. |
| **Task Scheduler** | Manage persistent cron jobs and one-time reminders. |
| **System Controller** | Monitor CPU/Memory, restart services, and manage processes. |
| **File Manager** | Search, read, write, and manipulate local files and directories. |
| **Browser Controller** | Web scraping, screenshots, and automated web interaction. |

---

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** (Running locally with `ollama serve`)
- **Telegram Bot Token** (From [@BotFather](https://t.me/botfather))

### 2. Installation
```bash
git clone https://github.com/M-Dev-Lab/ultimate-agent.git
cd ultimate-agent/python-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and ADMIN_TELEGRAM_IDS
```

### 4. Run the Agent
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## ⌨️ Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show the main menu. |
| `/help` | Display command reference and help categories. |
| `/status` | Check system resources and agent health. |
| `/build` | Launch the Project creation wizard. |
| `/post` | Launch the Social media posting wizard. |
| `/schedule` | Launch the Task scheduling wizard. |
| `/skills` | List and manage available skills. |

---

## 🚀 Deployment & Production

### Systemd (Recommended)
```bash
# 1. Copy service file
sudo cp systemd/ultimate-agent-python.service /etc/systemd/system/

# 2. Enable and Start
sudo systemctl daemon-reload
sudo systemctl enable ultimate-agent-python.service
sudo systemctl start ultimate-agent-python.service
```

### Docker
```bash
docker-compose up -d
```

### Monitoring
- **Health Check**: `GET http://localhost:8000/health`
- **Analytics Metrics**: `GET http://localhost:8000/api/v1/health/analytics`
- **Prometheus**: Metrics available on port `8001/metrics`.

---

## 🧪 Testing

The agent includes a comprehensive test suite (37+ tests) covering environment readiness and core logic.

```bash
cd python-agent
source venv/bin/activate
# Run all tests
pytest tests/ -v
```

---

## 📁 Project Structure

```text
.
├── python-agent/           # Core Python codebase
│   ├── app/
│   │   ├── core/           # Memory, Error Handling, Config
│   │   ├── db/             # Database session and vector models
│   │   ├── integrations/   # Telegram, Ollama, Browser, File
│   │   ├── models/         # SQLAlchemy schemas
│   │   ├── monitoring/     # Analytics and health
│   │   └── skills/         # Skill registry and implementations
│   └── tests/              # Comprehensive test suite
├── archive/                # Archived legacy TypeScript code
├── data/                   # Persistent storage (DB, logs)
└── SOUL.md                 # Agent personality and identity
```

---

## 📜 Documentation

- [Setup Guide](python-agent/LOCAL_SETUP_GUIDE.md)
- [API Documentation](python-agent/API_DOCUMENTATION.md)
- [Knowledge Base](KNOWLEDGE_BASE.md)

---

**Consolidated & Optimized**: February 2026.  
**Maintained by**: M-Dev-Lab Team.
