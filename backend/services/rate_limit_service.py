from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from services.db_connection import get_shared_engine

load_dotenv()


class RateLimitService:
    """
    PostgreSQL-based persistent rate limiting service.
    Stores rate limit data in PostgreSQL to survive server restarts.
    """

    def __init__(self) -> None:
        self.engine = get_shared_engine()
        self._initialized = False

    async def _init_db(self) -> None:
        """Initialize PostgreSQL tables if needed."""
        async with AsyncSession(self.engine) as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    ip VARCHAR(255) NOT NULL,
                    request_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ip, request_time)
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_rate_limits_ip_time ON rate_limits(ip, request_time)
            """))
            await session.commit()
            self._initialized = True

    async def check_rate_limit(self, ip: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if IP has exceeded rate limit.
        Returns True if request is allowed, False if rate limit exceeded.
        """
        await self._ensure_init()
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)

        async with AsyncSession(self.engine) as session:
            # Clean old entries outside the window
            await session.execute(
                text("""
                    DELETE FROM rate_limits
                    WHERE request_time < :cutoff_time
                """),
                {"cutoff_time": cutoff_time}
            )

            # Count requests in the window
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM rate_limits
                    WHERE ip = :ip AND request_time >= :cutoff_time
                """),
                {"ip": ip, "cutoff_time": cutoff_time}
            )
            count = result.scalar() or 0

            # Check if limit exceeded
            if count >= max_requests:
                await session.commit()
                return False

            # Add current request
            await session.execute(
                text("""
                    INSERT INTO rate_limits (ip, request_time)
                    VALUES (:ip, CURRENT_TIMESTAMP)
                """),
                {"ip": ip}
            )
            await session.commit()
            return True

    async def get_rate_limit_status(self, ip: str, max_requests: int, window_seconds: int) -> Dict[str, int]:
        """Get current rate limit status for an IP."""
        await self._ensure_init()
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)

        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM rate_limits
                    WHERE ip = :ip AND request_time >= :cutoff_time
                """),
                {"ip": ip, "cutoff_time": cutoff_time}
            )
            count = result.scalar() or 0

        return {
            "current": count,
            "limit": max_requests,
            "remaining": max(0, max_requests - count),
        }

    async def _ensure_init(self) -> None:
        """Ensure database is initialized."""
        try:
            async with AsyncSession(self.engine) as session:
                await session.execute(text("SELECT 1 FROM rate_limits LIMIT 1"))
        except Exception:
            await self._init_db()


rate_limit_service = RateLimitService()
