from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta

from dotenv import load_dotenv


class RateLimitService:
    """
    SQLite-based persistent rate limiting service.
    Stores rate limit data in SQLite database to survive server restarts.
    """

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")

        # Create data directory if it doesn't exist
        data_dir = backend_root / "data"
        data_dir.mkdir(exist_ok=True)

        db_path = os.getenv("RATE_LIMIT_DB_PATH", str(data_dir / "rate_limit.db"))
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables if needed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip TEXT NOT NULL,
                request_time REAL NOT NULL,
                PRIMARY KEY (ip, request_time)
            )
            """
        )
        # Create index for faster queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ip_time ON rate_limits(ip, request_time)
            """
        )
        conn.commit()
        conn.close()

    def check_rate_limit(self, ip: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if IP has exceeded rate limit.
        Returns True if request is allowed, False if rate limit exceeded.
        """
        now = datetime.now().timestamp()
        cutoff_time = now - window_seconds

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clean old entries outside the window
        cursor.execute(
            """
            DELETE FROM rate_limits
            WHERE request_time < ?
            """,
            (cutoff_time,),
        )

        # Count requests in the window
        cursor.execute(
            """
            SELECT COUNT(*) FROM rate_limits
            WHERE ip = ? AND request_time >= ?
            """,
            (ip, cutoff_time),
        )
        count = cursor.fetchone()[0]

        # Check if limit exceeded
        if count >= max_requests:
            conn.close()
            return False

        # Add current request
        cursor.execute(
            """
            INSERT INTO rate_limits (ip, request_time)
            VALUES (?, ?)
            """,
            (ip, now),
        )
        conn.commit()
        conn.close()
        return True

    def get_rate_limit_status(self, ip: str, max_requests: int, window_seconds: int) -> Dict[str, int]:
        """Get current rate limit status for an IP."""
        now = datetime.now().timestamp()
        cutoff_time = now - window_seconds

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM rate_limits
            WHERE ip = ? AND request_time >= ?
            """,
            (ip, cutoff_time),
        )
        count = cursor.fetchone()[0]
        conn.close()

        return {
            "current": count,
            "limit": max_requests,
            "remaining": max(0, max_requests - count),
        }


rate_limit_service = RateLimitService()
