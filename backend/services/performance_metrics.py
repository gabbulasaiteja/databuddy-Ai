from __future__ import annotations

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv


class PerformanceMetrics:
    """
    Tracks query performance metrics.
    """

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")

        # Create data directory if it doesn't exist
        data_dir = backend_root / "data"
        data_dir.mkdir(exist_ok=True)

        db_path = os.getenv("METRICS_DB_PATH", str(data_dir / "metrics.db"))
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database for metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS query_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT NOT NULL,
                sql TEXT NOT NULL,
                query_type TEXT NOT NULL,
                execution_time_ms REAL NOT NULL,
                rows_returned INTEGER DEFAULT 0,
                rows_affected INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON query_metrics(timestamp)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_query_type ON query_metrics(query_type)
            """
        )
        conn.commit()
        conn.close()

    def record_query(
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO query_metrics 
            (query_id, sql, query_type, execution_time_ms, rows_returned, rows_affected, success, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                sql[:500],  # Limit SQL length
                query_type,
                execution_time_ms,
                rows_returned,
                rows_affected,
                1 if success else 0,
                error_message[:500] if error_message else None,
                timestamp,
            ),
        )
        conn.commit()
        conn.close()

    def get_metrics(
        self,
        hours: int = 24,
        query_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get performance metrics for the last N hours."""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if query_type:
            cursor.execute(
                """
                SELECT * FROM query_metrics
                WHERE timestamp >= ? AND query_type = ?
                ORDER BY timestamp DESC
                LIMIT 1000
                """,
                (cutoff_time, query_type),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM query_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 1000
                """,
                (cutoff_time,),
            )
        
        rows = cursor.fetchall()
        conn.close()
        
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
        successful_queries = sum(1 for r in rows if r["success"])
        failed_queries = total_queries - successful_queries
        total_execution_time = sum(r["execution_time_ms"] for r in rows)
        avg_execution_time = total_execution_time / total_queries if total_queries > 0 else 0
        
        queries_by_type = defaultdict(int)
        for row in rows:
            queries_by_type[row["query_type"]] += 1
        
        recent_queries = [
            {
                "query_id": row["query_id"],
                "query_type": row["query_type"],
                "execution_time_ms": row["execution_time_ms"],
                "success": bool(row["success"]),
                "timestamp": row["timestamp"],
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


performance_metrics = PerformanceMetrics()
