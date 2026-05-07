import logging
from collections.abc import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _create_db_engine() -> Engine:
    try:
        engine: Engine = create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
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


engine: Engine = _create_db_engine()


SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, autocommit=False, autoflush=False,)

class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
