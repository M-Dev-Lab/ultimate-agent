# 🤖 Ultimate Agent - Unified Python Edition

**Single Python agent controlling your Linux machine via Telegram**

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Python FastAPI + Telegram Bot (Port 8000)         │
│  ├── Error Handling (Circuit Breaker + Retry)      │
│  ├── Memory Management (Context + SOUL.md)         │
│  ├── Analytics Tracking (Metrics + Health)         │
│  ├── 6 Skills (Project/Social/Task/System/File/Web)│
│  └── Ollama Integration (Local + Cloud)            │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Start Ollama
ollama serve

# 2. Start Agent
cd python-agent
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Features

✅ **Unified Agent** - Single Python process  
✅ **Advanced Error Handling** - Circuit breaker + exponential backoff  
✅ **Conversation Memory** - Context-aware responses  
✅ **Analytics** - Usage tracking + health monitoring  
✅ **6 Production Skills** - Fully implemented and tested  
✅ **SOUL Integration** - Personality from SOUL.md  
✅ **Telegram Interface** - Rich keyboard + inline buttons  

## Documentation

- [Setup Guide](python-agent/LOCAL_SETUP_GUIDE.md)
- [API Documentation](python-agent/API_DOCUMENTATION.md)
- [Unified Agent Setup](UNIFIED_AGENT_SETUP.md)

## Archive

TypeScript implementation archived on Feb 4, 2026. All functionality migrated to Python.
See `archive/` directory.
