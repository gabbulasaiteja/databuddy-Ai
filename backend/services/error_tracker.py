from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import logging
from collections import defaultdict

from services.db_connection import get_shared_engine

load_dotenv()
logger = logging.getLogger("databuddy")


class ErrorTracker:
    """
    PostgreSQL-based error tracking service.
    """

    def __init__(self) -> None:
        self.engine = get_shared_engine()
        self.enabled = os.getenv("ERROR_TRACKING_ENABLED", "true").lower() == "true"
        self._initialized = False

    async def _init_db(self) -> None:
        """Initialize PostgreSQL tables if needed."""
        if not self.enabled:
            return
        
        async with AsyncSession(self.engine) as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS errors (
                    id SERIAL PRIMARY KEY,
                    error_type VARCHAR(255) NOT NULL,
                    error_message TEXT NOT NULL,
                    error_category VARCHAR(100) NOT NULL,
                    context TEXT,
                    stack_trace TEXT,
                    user_id VARCHAR(255) DEFAULT 'default',
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp DESC)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_errors_category ON errors(error_category)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_errors_resolved ON errors(resolved)
            """))
            await session.commit()
            self._initialized = True

    async def track_error(
        self,
        error_type: str,
        error_message: str,
        error_category: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        user_id: str = "default",
    ) -> None:
        """Track an error."""
        if not self.enabled:
            return
        
        try:
            await self._ensure_init()
            async with AsyncSession(self.engine) as session:
                context_str = str(context)[:1000] if context else None
                stack_trace_str = stack_trace[:2000] if stack_trace else None
                
                await session.execute(
                    text("""
                        INSERT INTO errors 
                        (error_type, error_message, error_category, context, stack_trace, user_id, timestamp)
                        VALUES (:error_type, :error_message, :error_category, :context, :stack_trace, :user_id, CURRENT_TIMESTAMP)
                    """),
                    {
                        "error_type": error_type,
                        "error_message": error_message[:500],
                        "error_category": error_category,
                        "context": context_str,
                        "stack_trace": stack_trace_str,
                        "user_id": user_id,
                    }
                )
                await session.commit()
                
                # Log error
                logger.error(
                    f"Error tracked: {error_type} - {error_category} - {error_message[:200]}"
                )
        except Exception as e:
            logger.error(f"Failed to track error: {e}")

    async def get_error_stats(
        self,
        hours: int = 24,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.enabled:
            return {"total_errors": 0, "errors_by_category": {}, "recent_errors": []}
        
        await self._ensure_init()
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            async with AsyncSession(self.engine) as session:
                if category:
                    result = await session.execute(
                        text("""
                            SELECT * FROM errors
                            WHERE timestamp >= :cutoff_time AND error_category = :category AND resolved = FALSE
                            ORDER BY timestamp DESC
                            LIMIT 100
                        """),
                        {"cutoff_time": cutoff_time, "category": category}
                    )
                else:
                    result = await session.execute(
                        text("""
                            SELECT * FROM errors
                            WHERE timestamp >= :cutoff_time AND resolved = FALSE
                            ORDER BY timestamp DESC
                            LIMIT 100
                        """),
                        {"cutoff_time": cutoff_time}
                    )
                
                rows = result.fetchall()
                
                if not rows:
                    return {
                        "total_errors": 0,
                        "errors_by_category": {},
                        "recent_errors": [],
                    }
                
                errors_by_category = defaultdict(int)
                for row in rows:
                    errors_by_category[row[3]] += 1  # error_category is column index 3
                
                recent_errors = [
                    {
                        "error_type": row[1],
                        "error_category": row[3],
                        "error_message": row[2][:200],
                        "timestamp": row[8].isoformat() if hasattr(row[8], 'isoformat') else str(row[8]),
                    }
                    for row in rows[:10]
                ]
                
                return {
                    "total_errors": len(rows),
                    "errors_by_category": dict(errors_by_category),
                    "recent_errors": recent_errors,
                }
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {"total_errors": 0, "errors_by_category": {}, "recent_errors": []}

    async def _ensure_init(self) -> None:
        """Ensure database is initialized."""
        if not self.enabled:
            return
        if not self._initialized:
            try:
                async with AsyncSession(self.engine) as session:
                    await session.execute(text("SELECT 1 FROM errors LIMIT 1"))
                self._initialized = True
            except Exception:
                await self._init_db()
                self._initialized = True


error_tracker = ErrorTracker()
