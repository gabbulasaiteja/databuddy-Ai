from __future__ import annotations

import asyncio
from typing import Dict, Optional
from datetime import datetime
import uuid


class QueryTracker:
    """
    Tracks running queries for cancellation support.
    """

    def __init__(self) -> None:
        self.running_queries: Dict[str, asyncio.Task] = {}
        self.query_metadata: Dict[str, Dict] = {}

    def register_query(self, query_id: str, task: asyncio.Task, sql: str, user_id: str = "default") -> None:
        """Register a running query."""
        self.running_queries[query_id] = task
        self.query_metadata[query_id] = {
            "sql": sql,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }

    def cancel_query(self, query_id: str) -> bool:
        """Cancel a running query. Returns True if cancelled, False if not found."""
        if query_id not in self.running_queries:
            return False
        
        task = self.running_queries[query_id]
        if not task.done():
            task.cancel()
            self.query_metadata[query_id]["status"] = "cancelled"
            self.query_metadata[query_id]["cancelled_at"] = datetime.utcnow().isoformat()
            return True
        
        return False

    def complete_query(self, query_id: str) -> None:
        """Mark a query as completed."""
        if query_id in self.running_queries:
            del self.running_queries[query_id]
        if query_id in self.query_metadata:
            self.query_metadata[query_id]["status"] = "completed"
            self.query_metadata[query_id]["completed_at"] = datetime.utcnow().isoformat()

    def get_query_status(self, query_id: str) -> Optional[Dict]:
        """Get status of a query."""
        return self.query_metadata.get(query_id)

    def is_running(self, query_id: str) -> bool:
        """Check if a query is currently running."""
        if query_id not in self.running_queries:
            return False
        task = self.running_queries[query_id]
        return not task.done()

    def cleanup_completed(self) -> None:
        """Clean up completed queries from metadata (keep last 100)."""
        completed = [
            (qid, meta) for qid, meta in self.query_metadata.items()
            if meta.get("status") in ["completed", "cancelled"]
        ]
        if len(completed) > 100:
            # Remove oldest completed queries
            completed.sort(key=lambda x: x[1].get("completed_at", x[1].get("cancelled_at", "")))
            for qid, _ in completed[:-100]:
                del self.query_metadata[qid]


query_tracker = QueryTracker()
