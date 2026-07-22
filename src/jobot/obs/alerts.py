import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertMessage(BaseModel):
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertDispatcher:
    """
    Notification & Real-Time Alert Dispatcher (Layer L).
    Dispatches operational milestone notifications and high-severity incident alerts.
    """

    def __init__(self) -> None:
        self.alert_history: List[AlertMessage] = []

    def dispatch_alert(self, title: str, message: str, level: AlertLevel = AlertLevel.INFO) -> AlertMessage:
        alert = AlertMessage(
            alert_id=f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            level=level,
            title=title,
            message=message,
        )
        self.alert_history.append(alert)
        logger.info(f"[AlertDispatcher] [{level.value}] {title}: {message}")
        return alert

    def get_unread_alerts(self, min_level: AlertLevel = AlertLevel.INFO) -> List[AlertMessage]:
        return [a for a in self.alert_history if a.level.value >= min_level.value]
