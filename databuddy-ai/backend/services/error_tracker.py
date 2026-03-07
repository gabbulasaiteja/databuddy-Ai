from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging
from collections import defaultdict

logger = logging.getLogger("databuddy")


class ErrorTracker:
    """
    Tracks errors for monitoring and debugging.
    """

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")

        # Create data directory if it doesn't exist
        data_dir = backend_root / "data"
        data_dir.mkdir(exist_ok=True)

        db_path = os.getenv("ERROR_TRACKER_DB_PATH", str(data_dir / "errors.db"))
        self.db_path = db_path
        self.enabled = os.getenv("ERROR_TRACKING_ENABLED", "true").lower() == "true"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database for error tracking."""
        if not self.enabled:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_category TEXT NOT NULL,
                context TEXT,
                stack_trace TEXT,
                user_id TEXT DEFAULT 'default',
                timestamp TEXT NOT NULL,
                resolved INTEGER DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON errors(timestamp)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_category ON errors(error_category)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resolved ON errors(resolved)
            """
        )
        conn.commit()
        conn.close()

    def track_error(
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            timestamp = datetime.utcnow().isoformat()
            
            context_str = str(context)[:1000] if context else None
            stack_trace_str = stack_trace[:2000] if stack_trace else None
            
            cursor.execute(
                """
                INSERT INTO errors 
                (error_type, error_message, error_category, context, stack_trace, user_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    error_type,
                    error_message[:500],
                    error_category,
                    context_str,
                    stack_trace_str,
                    user_id,
                    timestamp,
                ),
            )
            conn.commit()
            conn.close()
            
            # Log error
            logger.error(
                f"Error tracked: {error_type} - {error_category} - {error_message[:200]}"
            )
        except Exception as e:
            logger.error(f"Failed to track error: {e}")

    def get_error_stats(
        self,
        hours: int = 24,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.enabled:
            return {"total_errors": 0, "errors_by_category": {}, "recent_errors": []}
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if category:
                cursor.execute(
                    """
                    SELECT * FROM errors
                    WHERE timestamp >= ? AND error_category = ? AND resolved = 0
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """,
                    (cutoff_time, category),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM errors
                    WHERE timestamp >= ? AND resolved = 0
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """,
                    (cutoff_time,),
                )
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return {
                    "total_errors": 0,
                    "errors_by_category": {},
                    "recent_errors": [],
                }
            
            errors_by_category = defaultdict(int)
            for row in rows:
                errors_by_category[row["error_category"]] += 1
            
            recent_errors = [
                {
                    "error_type": row["error_type"],
                    "error_category": row["error_category"],
                    "error_message": row["error_message"][:200],
                    "timestamp": row["timestamp"],
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


error_tracker = ErrorTracker()
