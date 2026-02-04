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

from app.core.config import settings
from app.models.schemas import ErrorResponse
from app.api import build_router, analysis_router, health_router, websocket_router, memory_router
from app.db.session import init_db, close_db
from app.memory import init_memory_system, shutdown_memory_system
from app.integrations.telegram_bot import init_telegram_bot, start_telegram_bot, stop_telegram_bot, notify_admin_on_startup

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Secure AI-Powered Coding Agent (Python)",
    debug=settings.debug,
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


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


# ==================== Telegram Webhook Endpoint ====================

@app.post("/telegram/webhook", tags=["Telegram"])
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    from telegram import Update
    from app.integrations.telegram_bot import get_telegram_bot
    
    bot = get_telegram_bot()
    if not bot.application:
        return {"status": "ok", "message": "Bot not initialized"}
    
    try:
        data = await request.json()
        update = Update.de_json(data, bot.application.bot)
        await bot.application.process_update(update)
    except KeyError as e:
        # Handle missing fields in test data
        logger.warning(f"Telegram webhook missing field: {e}")
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
    
    return {"status": "ok"}


# ==================== Ready for Route Imports ====================
# Register API routes
app.include_router(build_router)
app.include_router(analysis_router)
app.include_router(health_router)
app.include_router(websocket_router)
app.include_router(memory_router)

logger.info("FastAPI application initialized", app=settings.app_name, version=settings.app_version)


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
        
        # Initialize and start Telegram bot
        logger.info("Initializing Telegram bot...")
        await init_telegram_bot()
        logger.info("Telegram bot initialized, starting...")
        await start_telegram_bot()
        logger.info("Telegram bot started")
        
        # Send startup notification to admin
        logger.info("Sending startup notification to admin...")
        await notify_admin_on_startup()
        logger.info("Startup notification sent")
        
        logger.info("=" * 60)
        logger.info("🚀 ULTIMATE CODING AGENT STARTED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("Startup initialization failed", error=str(e), exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    logger.info("Shutting down application")
    try:
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
