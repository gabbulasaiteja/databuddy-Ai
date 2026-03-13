from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from services.db_connection import get_shared_engine

load_dotenv()


class HistoryService:
    """
    PostgreSQL-based persistent query history service.
    """

    def __init__(self) -> None:
        self.engine = get_shared_engine()
        self._initialized = False

    async def _init_db(self) -> None:
        """Initialize PostgreSQL tables if needed."""
        async with AsyncSession(self.engine) as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) DEFAULT 'default',
                    prompt TEXT NOT NULL,
                    sql_generated TEXT NOT NULL,
                    success BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC)
            """))
            await session.commit()
            self._initialized = True

    async def add_query(
        self,
        prompt: str,
        sql: str,
        success: bool = True,
        user_id: str = "default",
    ) -> int:
        """Add a query to the history."""
        await self._ensure_init()
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                text("""
                    INSERT INTO query_history (user_id, prompt, sql_generated, success, created_at)
                    VALUES (:user_id, :prompt, :sql, :success, CURRENT_TIMESTAMP)
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "prompt": prompt,
                    "sql": sql,
                    "success": success,
                }
            )
            query_id = result.scalar()
            await session.commit()
            return query_id

    async def get_history(self, limit: int = 20, user_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve query history, most recent first."""
        await self._ensure_init()
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                text("""
                    SELECT id, prompt, sql_generated as sql, created_at as timestamp
                    FROM query_history
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit}
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "prompt": row[1],
                    "sql": row[2],
                    "timestamp": row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3]),
                }
                for row in rows
            ]

    async def _ensure_init(self) -> None:
        """Ensure database is initialized."""
        if not self._initialized:
            try:
                async with AsyncSession(self.engine) as session:
                    await session.execute(text("SELECT 1 FROM query_history LIMIT 1"))
                self._initialized = True
            except Exception:
                await self._init_db()
                self._initialized = True


history_service = HistoryService()
