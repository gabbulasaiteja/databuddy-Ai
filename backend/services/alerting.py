from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logger = logging.getLogger("databuddy")


class AlertingService:
    """
    Basic alerting system for monitoring failures and issues.
    """

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")
        
        self.enabled = os.getenv("ALERTING_ENABLED", "true").lower() == "true"
        self.error_threshold = int(os.getenv("ALERT_ERROR_THRESHOLD", "10"))  # Alert after N errors
        self.slow_query_threshold_ms = int(os.getenv("ALERT_SLOW_QUERY_MS", "5000"))  # Alert on slow queries
        
        # In-memory alert state (could be persisted)
        self.alert_history: List[Dict[str, Any]] = []
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # 5 minutes

    def check_and_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check conditions and send alert if threshold exceeded.
        Returns True if alert was sent.
        """
        if not self.enabled:
            return False
        
        # Check cooldown
        last_alert = self.last_alert_time.get(alert_type)
        if last_alert:
            time_since_last = (datetime.utcnow() - last_alert).total_seconds()
            if time_since_last < self.alert_cooldown_seconds:
                return False  # Still in cooldown
        
        # Send alert
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.alert_history.append(alert)
        self.last_alert_time[alert_type] = datetime.utcnow()
        
        # Log alert
        log_level = logging.ERROR if severity == "error" else logging.WARNING
        logger.log(
            log_level,
            f"ALERT [{severity.upper()}]: {alert_type} - {message}",
            extra={"alert": alert},
        )
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        return True

    def check_error_rate(
        self,
        error_count: int,
        time_window_hours: int = 1,
    ) -> bool:
        """Check if error rate exceeds threshold."""
        if error_count >= self.error_threshold:
            return self.check_and_alert(
                alert_type="high_error_rate",
                message=f"High error rate detected: {error_count} errors in last {time_window_hours} hour(s)",
                severity="error",
                context={"error_count": error_count, "threshold": self.error_threshold},
            )
        return False

    def check_slow_query(
        self,
        execution_time_ms: float,
        sql: str,
        query_type: str,
    ) -> bool:
        """Check if query is slow and alert."""
        if execution_time_ms >= self.slow_query_threshold_ms:
            return self.check_and_alert(
                alert_type="slow_query",
                message=f"Slow query detected: {execution_time_ms:.0f}ms ({query_type})",
                severity="warning",
                context={
                    "execution_time_ms": execution_time_ms,
                    "query_type": query_type,
                    "sql_preview": sql[:200],
                },
            )
        return False

    def get_alerts(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) >= cutoff_time
        ]
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        return alerts[-50:]  # Return last 50


alerting_service = AlertingService()
