from __future__ import annotations

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from services.db_connection import get_shared_engine

load_dotenv()


class PerformanceMetrics:
    """
    PostgreSQL-based query performance metrics tracking.
    """

    def __init__(self) -> None:
        self.engine = get_shared_engine()
        self._initialized = False

    async def _init_db(self) -> None:
        """Initialize PostgreSQL tables if needed."""
        async with AsyncSession(self.engine) as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS query_metrics (
                    id SERIAL PRIMARY KEY,
                    query_id VARCHAR(255) NOT NULL,
                    sql TEXT NOT NULL,
                    query_type VARCHAR(50) NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    rows_returned INTEGER DEFAULT 0,
                    rows_affected INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_metrics_timestamp ON query_metrics(timestamp DESC)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_metrics_query_type ON query_metrics(query_type)
            """))
            await session.commit()
            self._initialized = True

    async def record_query(
        self,
        query_id: str,
        sql: str,
        query_type: str,
        execution_time_ms: float,
        rows_returned: int = 0,
        rows_affected: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a query metric."""
        await self._ensure_init()
        async with AsyncSession(self.engine) as session:
            await session.execute(
                text("""
                    INSERT INTO query_metrics 
                    (query_id, sql, query_type, execution_time_ms, rows_returned, rows_affected, success, error_message, timestamp)
                    VALUES (:query_id, :sql, :query_type, :execution_time_ms, :rows_returned, :rows_affected, :success, :error_message, CURRENT_TIMESTAMP)
                """),
                {
                    "query_id": query_id,
                    "sql": sql[:500],  # Limit SQL length
                    "query_type": query_type,
                    "execution_time_ms": execution_time_ms,
                    "rows_returned": rows_returned,
                    "rows_affected": rows_affected,
                    "success": success,
                    "error_message": error_message[:500] if error_message else None,
                }
            )
            await session.commit()

    async def get_metrics(
        self,
        hours: int = 24,
        query_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get performance metrics for the last N hours."""
        await self._ensure_init()
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with AsyncSession(self.engine) as session:
            if query_type:
                result = await session.execute(
                    text("""
                        SELECT * FROM query_metrics
                        WHERE timestamp >= :cutoff_time AND query_type = :query_type
                        ORDER BY timestamp DESC
                        LIMIT 1000
                    """),
                    {"cutoff_time": cutoff_time, "query_type": query_type}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM query_metrics
                        WHERE timestamp >= :cutoff_time
                        ORDER BY timestamp DESC
                        LIMIT 1000
                    """),
                    {"cutoff_time": cutoff_time}
                )
            
            rows = result.fetchall()
            
            if not rows:
                return {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "avg_execution_time_ms": 0,
                    "total_execution_time_ms": 0,
                    "queries_by_type": {},
                    "recent_queries": [],
                }
            
            total_queries = len(rows)
            successful_queries = sum(1 for r in rows if r[7])  # success is column index 7
            failed_queries = total_queries - successful_queries
            total_execution_time = sum(r[4] for r in rows)  # execution_time_ms is column index 4
            avg_execution_time = total_execution_time / total_queries if total_queries > 0 else 0
            
            queries_by_type = defaultdict(int)
            for row in rows:
                queries_by_type[row[3]] += 1  # query_type is column index 3
            
            recent_queries = [
                {
                    "query_id": row[1],
                    "query_type": row[3],
                    "execution_time_ms": row[4],
                    "success": bool(row[7]),
                    "timestamp": row[9].isoformat() if hasattr(row[9], 'isoformat') else str(row[9]),
                }
                for row in rows[:10]
            ]
            
            return {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "failed_queries": failed_queries,
                "avg_execution_time_ms": round(avg_execution_time, 2),
                "total_execution_time_ms": round(total_execution_time, 2),
                "queries_by_type": dict(queries_by_type),
                "recent_queries": recent_queries,
            }

    async def _ensure_init(self) -> None:
        """Ensure database is initialized."""
        if not self._initialized:
            try:
                async with AsyncSession(self.engine) as session:
                    await session.execute(text("SELECT 1 FROM query_metrics LIMIT 1"))
                self._initialized = True
            except Exception:
                await self._init_db()
                self._initialized = True


performance_metrics = PerformanceMetrics()
