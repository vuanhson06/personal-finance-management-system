"""
database.py — SQLAlchemy Engine, Session, and Base Configuration
================================================================
This module is the single entry point for all database connectivity.
It creates the SQLAlchemy Engine (with connection pooling), the SessionLocal
factory for managing database sessions, and the DeclarativeBase that all
ORM models in this project will inherit from.

Usage:
    - Import `SessionLocal` or use the `get_db()` dependency in service modules.
    - Import `Base` in all ORM model files for table mapping.

Directive Reference: directives/backend_logic_rules.md — Section 1 & 4
                     directives/db_rules.md — Section 4 (Security Protocols)
"""

import logging
from collections.abc import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

# Configure a module-level logger to capture DB connection events internally
# without ever exposing stack traces to the end user.
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# =============================================================================
# Engine Creation
# =============================================================================

def _create_db_engine() -> Engine:
    """
    Initializes and returns the SQLAlchemy Engine for MySQL.

    Configures connection pooling to efficiently handle multiple concurrent
    requests from the application. Validates the connection immediately on
    startup so misconfiguration is discovered at launch, not at runtime.

    Pool Configuration:
        - pool_size=5:      Number of persistent connections to keep open.
        - max_overflow=10:  Maximum extra connections allowed beyond pool_size.
        - pool_pre_ping=True: Validates each connection before use, recovering
                              from dropped DB connections gracefully.

    Returns:
        A configured SQLAlchemy Engine instance.

    Raises:
        OperationalError: Caught internally; logs the error and re-raises a
                          clean RuntimeError to the caller.
    """
    try:
        engine: Engine = create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        # Eagerly test the connection at startup to validate credentials.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info(
            "Database engine created successfully. "
            "Connected to '%s' on %s:%s.",
            settings.db_name,
            settings.db_host,
            settings.db_port,
        )
        return engine

    except OperationalError as e:
        logger.error(
            "CRITICAL: Failed to connect to the database. "
            "Verify DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD in your .env file. "
            "Original error: %s",
            e,
        )
        raise RuntimeError(
            "Database connection failed. Please check your configuration."
        ) from e


# Module-level engine singleton — created once at import time.
engine: Engine = _create_db_engine()


# =============================================================================
# Session Factory
# =============================================================================

# SessionLocal is the factory for creating new database session objects.
# autocommit=False: Transactions must be committed explicitly for data integrity.
# autoflush=False:  Prevents automatic flushes before queries to avoid
#                   partial writes and unexpected DB interactions.
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Declarative Base
# =============================================================================

class Base(DeclarativeBase):
    """
    The base class for all SQLAlchemy ORM models in this project.
    All table models (Users, Income, Expenses, etc.) must inherit from this class.
    Using SQLAlchemy 2.0+ style DeclarativeBase for full type-hint support.
    """
    pass


# =============================================================================
# Session Lifecycle Dependency
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provides a managed database session for service/logic modules.

    This generator function guarantees that every session is properly closed
    after use, even if an exception occurs during the operation. Use this as
    the standard method for obtaining a session throughout the backend.

    Yields:
        Session: An active SQLAlchemy database session.

    Example:
        db: Session = next(get_db())
        # ... perform queries ...
        # Session is closed automatically after the generator is exhausted.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
