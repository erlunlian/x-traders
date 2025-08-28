import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

# Using psycopg3 with asyncpg for async operations
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    isolation_level="READ COMMITTED",  # Explicit - fine for single-writer per symbol
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db_transaction():
    """Provide transactional scope for atomic operations"""
    async with async_session() as session:
        async with session.begin():
            yield session


async def get_db():
    """For dependency injection in FastAPI"""
    async with async_session() as session:
        yield session


async def init_db():
    """Initialize database - with SQLModel tables are created via migrations"""
    # Import all models to ensure they are registered with SQLModel
    import database.models  # noqa: F401

    # With Alembic migrations, we don't need to create tables here
    # Tables are created via migrations using './x db upgrade'
    pass
