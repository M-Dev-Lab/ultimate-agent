"""
Main FastAPI application with security configuration
"""

import logging
import sys
import structlog
from pathlib import Path

# Configure logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure file handler for debugging
file_handler = logging.FileHandler(LOGS_DIR / "app.log", mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))

# Configure structured logging FIRST
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get root logger and add file handler
logger = structlog.get_logger()

# Add file handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.DEBUG)

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime
from typing import Optional
import asyncio

from app.core.config import settings
from app.models.schemas import ErrorResponse
from app.api import build_router, analysis_router, health_router, websocket_router, memory_router
from app.db.session import init_db, close_db
from app.memory import init_memory_system, shutdown_memory_system
from app.integrations.telegram_bot import init_telegram_bot, start_telegram_bot, stop_telegram_bot, notify_admin_on_startup
from app.agents.autonomous import AutonomousWorker
from app.agents.brain import AgentBrain
from app.mcp.manager import MCPServerManager

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous AI-Powered Coding Agent with MCP Integration (Python)",
    debug=settings.debug,
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Global instances for autonomous operation
autonomous_worker: Optional[AutonomousWorker] = None
agent_brain: Optional[AgentBrain] = None
mcp_manager: Optional[MCPServerManager] = None


# ==================== Middleware Configuration ====================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (prevent Host header attacks)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"],
)


# ==================== Exception Handlers ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.error(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "detail": "Invalid request data",
            "status_code": 422,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        exception=str(exc),
        exc_info=True,
    )

    # Don't expose internal errors in production
    detail = str(exc) if settings.debug else "Internal server error"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "detail": detail,
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ==================== Request/Response Logging ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses"""
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    response = await call_next(request)

    logger.info(
        "response_sent",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )

    return response


# ==================== Security Headers Middleware ====================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:;"
    )

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), "
        "camera=(), "
        "microphone=(), "
        "geolocation=(), "
        "payment=()"
    )

    return response


# ==================== Health Check Endpoint ====================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
    }


# ==================== Telegram Integration ====================
# The Unified Python Agent handles all Telegram interactions (Phase 2.0)
# 
# @app.post("/telegram/webhook", tags=["Telegram"])
# async def telegram_webhook(request: Request):
#     """Handle Telegram webhook updates"""
#     from telegram import Update
#     from app.integrations.telegram_bot import get_telegram_bot
#     
#     bot = get_telegram_bot()
#     if not bot.application:
#         return {"status": "ok", "message": "Bot not initialized"}
#     
#     try:
#         data = await request.json()
#         update = Update.de_json(data, bot.application.bot)
#         await bot.application.process_update(update)
#     except KeyError as e:
#         # Handle missing fields in test data
#         logger.warning(f"Telegram webhook missing field: {e}")
#     except Exception as e:
#         logger.error(f"Telegram webhook error: {e}")
#     
#     return {"status": "ok"}


# ==================== Ready for Route Imports ====================
# Register API routes
app.include_router(build_router)
app.include_router(analysis_router)
app.include_router(health_router)
app.include_router(websocket_router)
app.include_router(memory_router)

logger.info("FastAPI application initialized", app=settings.app_name, version=settings.app_version)


# ==================== New Autonomous & MCP Endpoints ====================

@app.get("/autonomous/status", tags=["Autonomous"])
async def get_autonomous_status():
    """Get autonomous worker status"""
    if autonomous_worker:
        return autonomous_worker.get_status()
    return {"running": False, "message": "Autonomous mode not enabled"}

@app.post("/autonomous/toggle", tags=["Autonomous"])
async def toggle_autonomous(enabled: bool):
    """Toggle autonomous mode"""
    global autonomous_worker

    if enabled and not autonomous_worker:
        autonomous_worker = AutonomousWorker()
        asyncio.create_task(autonomous_worker.start())
        return {"autonomous_mode": True, "message": "Autonomous mode activated"}
    elif not enabled and autonomous_worker:
        autonomous_worker.stop()
        autonomous_worker = None
        return {"autonomous_mode": False, "message": "Autonomous mode deactivated"}

    return {"autonomous_mode": enabled, "message": "No change"}

@app.get("/mcp/servers", tags=["MCP"])
async def get_mcp_servers(category: Optional[str] = None):
    """Get available MCP servers"""
    if not mcp_manager:
        return {"error": "MCP integration not enabled"}

    return mcp_manager.get_available_servers(category)

@app.get("/mcp/stats", tags=["MCP"])
async def get_mcp_stats():
    """Get MCP manager statistics"""
    if not mcp_manager:
        return {"error": "MCP integration not enabled"}

    return mcp_manager.get_stats()

@app.post("/mcp/install/{server_name}", tags=["MCP"])
async def install_mcp_server(server_name: str):
    """Install an MCP server"""
    if not mcp_manager:
        return {"error": "MCP integration not enabled"}

    success = await mcp_manager.install_server(server_name)
    return {"success": success, "server": server_name}

@app.post("/task/analyze", tags=["Tasks"])
async def analyze_task(request: dict):
    """Analyze a task using Agent Brain"""
    if not agent_brain:
        return {"error": "Agent brain not initialized"}

    description = request.get("description", "")
    context = request.get("context", {})

    analysis = await agent_brain.analyze_request(description, context)
    return analysis

@app.post("/project/plan", tags=["Tasks"])
async def plan_project(request: dict):
    """Create a project plan"""
    if not agent_brain:
        return {"error": "Agent brain not initialized"}

    description = request.get("description", "")
    requirements = request.get("requirements", [])

    plan = await agent_brain.plan_project(description, requirements)
    return plan


# ==================== Startup and Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database, memory, and Telegram bot on startup"""
    logger.info("Starting application", app=settings.app_name)
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialization successful")
        
        # Initialize persistent memory system
        init_memory_system()
        logger.info("Persistent memory system initialized")
        
        # Test Ollama connection
        try:
            from app.integrations.ollama import get_ollama_client
            ollama = get_ollama_client()
            health = await ollama.health_check()
            logger.info(f"Ollama health check: {health}")
            if health.get("local"):
                logger.info(f"✅ Ollama Local connected: {health.get('models', [])}")
            if health.get("cloud"):
                logger.info("✅ Ollama Cloud connected")
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
        
        # Initialize and start Telegram bot (Python) if configured
        if settings.use_python_telegram:
            logger.info("Initializing Python Telegram bot...")
            await init_telegram_bot()
            logger.info("Telegram bot initialized, starting...")
            await start_telegram_bot()
            logger.info("Telegram bot started")

            # Send startup notification to admin
            logger.info("Sending startup notification to admin...")
            await notify_admin_on_startup()
            logger.info("Startup notification sent to admin")
        else:
            logger.info("Python Telegram bot disabled (set USE_PYTHON_TELEGRAM=true to enable).")

        # Initialize Agent Brain (Decision Engine)
        global agent_brain, mcp_manager
        agent_brain = AgentBrain()
        logger.info("🧠 Agent Brain initialized with Ollama Qwen3 Coder")

        # Initialize MCP Manager (if enabled)
        if settings.enable_mcp_servers:
            mcp_manager = MCPServerManager()
            logger.info(f"📦 MCP Manager initialized")

        # Start Autonomous Worker (if enabled)
        if settings.autonomous_mode:
            global autonomous_worker
            autonomous_worker = AutonomousWorker()
            # Start in background
            asyncio.create_task(autonomous_worker.start())
            logger.info(f"🤖 Autonomous Worker started (check interval: {settings.check_interval}s)")

        logger.info("=" * 60)
        logger.info("🚀 ULTIMATE LOCAL AI AGENT STARTED")
        logger.info(f"   Autonomous: {'YES' if settings.autonomous_mode else 'NO'} | MCP: {'YES' if settings.enable_mcp_servers else 'NO'}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("Startup initialization failed", error=str(e), exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    logger.info("Shutting down application")
    try:
        # Stop autonomous worker
        if autonomous_worker:
            autonomous_worker.stop()
            logger.info("Autonomous worker stopped")

        # Stop Telegram bot
        await stop_telegram_bot()
        logger.info("Telegram bot stopped")

        # Shutdown memory system (consolidates memory)
        shutdown_memory_system()
        logger.info("Memory system shutdown complete")

        # Close database connections
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
