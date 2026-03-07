from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv


class HistoryService:
    """
    SQLite-based persistent query history service.
    """

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")

        # Create data directory if it doesn't exist
        data_dir = backend_root / "data"
        data_dir.mkdir(exist_ok=True)

        db_path = os.getenv("HISTORY_DB_PATH", str(data_dir / "history.db"))
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables if needed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                prompt TEXT NOT NULL,
                sql_generated TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def add_query(
        self,
        prompt: str,
        sql: str,
        success: bool = True,
        user_id: str = "default",
    ) -> int:
        """Add a query to the history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO queries (user_id, prompt, sql_generated, success, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, prompt, sql, 1 if success else 0, timestamp),
        )
        query_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return query_id

    def get_history(self, limit: int = 20, user_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve query history, most recent first."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, prompt, sql_generated as sql, created_at as timestamp
            FROM queries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


history_service = HistoryService()
