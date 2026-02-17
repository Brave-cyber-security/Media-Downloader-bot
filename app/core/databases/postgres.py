from contextlib import asynccontextmanager
from functools import cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings.config import get_settings, Settings

settings: Settings = get_settings()


@cache
def get_async_engine():
    return create_async_engine(
        settings.get_async_postgres_url(),
        pool_size=3,
        max_overflow=5,
        future=True,
        echo=False,
    )


@cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_general_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session
