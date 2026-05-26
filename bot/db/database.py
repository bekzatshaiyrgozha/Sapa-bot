from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base
from bot import config
import asyncio
import logging

logger = logging.getLogger(__name__)

# create engine with a larger pool to reduce "another operation is in progress"
# errors under concurrency
engine = create_async_engine(
    config.DATABASE_URL,
    echo=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def retry_on_interface_error(coro_func):
    """Decorator to retry a coroutine once if asyncpg InterfaceError occurs."""

    async def wrapper(*args, **kwargs):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            # asyncpg InterfaceError often wraps as SQLAlchemy InterfaceError
            msg = str(e)
            if 'another operation is in progress' in msg:
                logger.warning('Transient DB concurrency error, retrying once: %s', e)
                await asyncio.sleep(0.05)
                return await coro_func(*args, **kwargs)
            raise

    return wrapper


# Simple global lock to serialize DB access where asyncpg reports concurrent-operation errors.
# This is a pragmatic workaround for environments with limited asyncpg concurrency.
_db_lock = None
_db_lock_loop = None


class locked_session:
    """Async context manager that acquires a global lock (created on the
    running event loop) before yielding an AsyncSession.

    This avoids creating an asyncio.Lock() at import time which can bind it to
    the wrong event loop and cause "attached to a different loop" errors.
    Use as: async with locked_session() as session: ...
    """

    def __init__(self):
        self._session = None
        self._lock = None

    async def __aenter__(self):
        global _db_lock, _db_lock_loop
        loop = asyncio.get_running_loop()
        if _db_lock is None or _db_lock_loop is not loop:
            _db_lock = asyncio.Lock()
            _db_lock_loop = loop
        self._lock = _db_lock
        await self._lock.acquire()
        self._session = AsyncSessionLocal()
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self._session.close()
        finally:
            try:
                self._lock.release()
            except Exception:
                pass
