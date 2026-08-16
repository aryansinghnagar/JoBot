import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


import json
import uuid
from pathlib import Path


class AlertMessage(BaseModel):
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


class AlertDispatcher:
    """
    Notification & Real-Time Alert Dispatcher (Layer L).
    Dispatches operational milestone notifications and high-severity incident alerts to ~/.jobot/alerts.jsonl.
    """

    def __init__(self, alert_file: Optional[Path] = None) -> None:
        if alert_file is None:
            alert_file = Path.home() / ".jobot" / "alerts.jsonl"
        self.alert_file = alert_file
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
        self.alert_history: List[AlertMessage] = []

    def dispatch_alert(self, title: str, message: str, level: AlertLevel = AlertLevel.INFO) -> AlertMessage:
        alert = AlertMessage(
            alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
            level=level,
            title=title,
            message=message,
        )
        self.alert_history.append(alert)
        logger.info(f"[AlertDispatcher] [{level.value}] {title}: {message}")

        with open(self.alert_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
            }) + "\n")

        return alert

    def list_alerts(self, unack_only: bool = False) -> List[Dict]:
        if not self.alert_file.exists():
            return []
        alerts = []
        with open(self.alert_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if unack_only and item.get("acknowledged"):
                        continue
                    alerts.append(item)
        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        alerts = self.list_alerts()
        found = False
        for a in alerts:
            if a["alert_id"] == alert_id or a["alert_id"].endswith(alert_id):
                a["acknowledged"] = True
                found = True
        if found:
            with open(self.alert_file, "w", encoding="utf-8") as f:
                for a in alerts:
                    f.write(json.dumps(a) + "\n")
        return found
