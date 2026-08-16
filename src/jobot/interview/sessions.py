"""Interview session persistence to ~/.jobot/interviews/<session_id>.json."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


def default_sessions_dir() -> Path:
    return Path.home() / ".jobot" / "interviews"


class InterviewTurn(BaseModel):
    question_id: str
    question_text: str
    track: str
    answer: str
    feedback: str
    star_score: float


class InterviewSession(BaseModel):
    session_id: str
    track: str
    status: str = "active"
    created_at: str
    updated_at: str
    turns: List[InterviewTurn] = []
    asked_ids: List[str] = []


class SessionStore:
    """Load/save interview sessions as JSON files."""

    def __init__(self, sessions_dir: Optional[Path] = None) -> None:
        self.sessions_dir = Path(sessions_dir or default_sessions_dir())
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def save(self, session: InterviewSession) -> Path:
        session.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._path(session.session_id)
        path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, session_id: str) -> Optional[InterviewSession]:
        path = self._path(session_id)
        if not path.exists():
            return None
        return InterviewSession.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> List[InterviewSession]:
        sessions = []
        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                sessions.append(
                    InterviewSession.model_validate_json(path.read_text(encoding="utf-8"))
                )
            except Exception:  # noqa: BLE001
                continue
        return sessions


def new_session(track: str) -> InterviewSession:
    now = datetime.now(timezone.utc).isoformat()
    return InterviewSession(
        session_id=f"int_{uuid.uuid4().hex[:8]}",
        track=track,
        created_at=now,
        updated_at=now,
    )
