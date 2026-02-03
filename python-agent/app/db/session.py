"""
Database session and connection management
Provides SQLAlchemy session factory and dependency injection
"""

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from typing import Generator
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from settings"""
    return settings.database_url.get_secret_value()


# Create engine with appropriate pool configuration
engine_kwargs = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,  # Test connections before using
}

# Only set connect_args for non-SQLite databases
db_url = get_database_url()
if "sqlite" not in db_url:
    engine_kwargs["connect_args"] = {
        "connect_timeout": 10,
    }

# Use different pool strategies based on environment
if settings.environment == "production":
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
else:
    engine_kwargs["poolclass"] = NullPool  # Create new connection for each request in dev

engine = create_engine(
    db_url,
    **engine_kwargs
)

# Add connection event listeners for connection pool
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Setup SQLite-specific pragmas if using SQLite"""
    if "sqlite" in get_database_url():
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for database session
    Usage: @app.get("/items/") def get_items(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database and create tables"""
    try:
        from app.models.database import Base
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db():
    """Close database connections"""
    engine.dispose()
    logger.info("Database connections closed")
