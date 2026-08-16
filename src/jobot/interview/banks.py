"""Question banks for mock interview sessions (behavioral / system design / technical)."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

TRACKS = ("behavioral", "system_design", "technical")


class InterviewQuestion(BaseModel):
    id: str
    track: str
    text: str
    difficulty: str = "medium"
    tags: List[str] = []


class QuestionBank:
    """Loads question banks from JSON files shipped in this package."""

    def __init__(self, bank_dir: Optional[Path] = None) -> None:
        self.bank_dir = Path(bank_dir or (Path(__file__).parent / "questions"))
        self._cache: Dict[str, List[InterviewQuestion]] = {}

    def _load_track(self, track: str) -> List[InterviewQuestion]:
        if track in self._cache:
            return self._cache[track]
        path = self.bank_dir / f"{track}.json"
        if not path.exists():
            raise ValueError(f"unknown interview track '{track}'; one of {TRACKS}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        questions = [InterviewQuestion(**item) for item in raw]
        self._cache[track] = questions
        return questions

    def questions(self, track: str) -> List[InterviewQuestion]:
        return self._load_track(track)

    def next_question(
        self,
        track: str,
        asked_ids: List[str],
        difficulty_ramp: int = 0,
    ) -> Optional[InterviewQuestion]:
        """Pick the next unasked question, ramping difficulty with progress."""
        pool = [q for q in self._load_track(track) if q.id not in asked_ids]
        if not pool:
            return None
        ordered = sorted(pool, key=lambda q: q.id)
        mid = min(difficulty_ramp, len(ordered) - 1)
        return ordered[mid]
