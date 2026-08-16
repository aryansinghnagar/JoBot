"""Two-tier job dedup service (plan.md Phase 2).

Tier 1: exact hash over normalized (title, company, location).
Tier 2: vector cosine similarity > threshold (default 0.92) over a local
pseudo-embedding (reuses `jobot.memory.vector.simple_embedding`, no new deps).

Persistence: `job_dedup_cache` table in the SQLite control plane DB.
"""

import hashlib
import logging
import re
from typing import List, Optional, Tuple

from jobot.memory.vector import simple_embedding
from jobot.models.domain import JobPosting
from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_THRESHOLD = 0.92

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class DedupResult:
    """Outcome of a dedup pass over a batch of postings."""

    def __init__(self, unique: List[JobPosting], rejected: int) -> None:
        self.unique = unique
        self.rejected = rejected

    @property
    def scraped(self) -> int:
        return len(self.unique) + self.rejected

    @property
    def repost_rate(self) -> float:
        """Fraction of the batch rejected as duplicates (0.0-1.0)."""
        if self.scraped == 0:
            return 0.0
        return self.rejected / self.scraped


class DedupService:
    """Persistent two-tier duplicate-posting detector."""

    def __init__(
        self, db: Optional[DatabaseManager] = None, threshold: float = DEFAULT_VECTOR_THRESHOLD
    ) -> None:
        self.db = db or DatabaseManager()
        self.threshold = threshold

    @staticmethod
    def normalize(text: str) -> str:
        return _NON_ALNUM.sub(" ", text.lower()).strip()

    @staticmethod
    def exact_hash(title: str, company: str, location: str) -> str:
        canonical = "|".join(DedupService.normalize(part) for part in (title, company, location))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _embed(posting: JobPosting) -> List[float]:
        # Title only: the exact-hash tier already keys on title|company|location,
        # and shared company/location text would drown the vector-tier signal.
        return simple_embedding(posting.title, dim=64)

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return dot  # both vectors are unit-normalized

    def is_duplicate(self, posting: JobPosting) -> bool:
        if self.db.dedup_hash_exists(
            self.exact_hash(posting.title, posting.company, posting.location)
        ):
            return True
        candidate = self._embed(posting)
        for entry in self.db.list_dedup_entries():
            if self.cosine(candidate, entry["embedding"]) >= self.threshold:
                return True
        return False

    def record(self, posting: JobPosting) -> None:
        self.db.save_dedup_entry(
            self.exact_hash(posting.title, posting.company, posting.location),
            posting.job_id,
            posting.title,
            posting.company,
            posting.location,
            self._embed(posting),
        )

    def filter_unique(self, postings: List[JobPosting]) -> DedupResult:
        """Record and keep first-seen postings; reject exact or near duplicates."""
        unique: List[JobPosting] = []
        rejected = 0
        for posting in postings:
            if self.is_duplicate(posting):
                rejected += 1
                continue
            self.record(posting)
            unique.append(posting)
        return DedupResult(unique=unique, rejected=rejected)

    @staticmethod
    def repost_reduction(synthetic: List[Tuple[JobPosting, bool]]) -> float:
        """Score a synthetic corpus: fraction of true duplicates the service rejected."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            service = DedupService(db=DatabaseManager(Path(tmp) / "dedup_test.db"))
            rejected_true_dupes = 0
            true_dupes = 0
            for posting, is_dupe in synthetic:
                if is_dupe:
                    true_dupes += 1
                    if service.is_duplicate(posting):
                        rejected_true_dupes += 1
                else:
                    service.record(posting)
        if true_dupes == 0:
            return 0.0
        return rejected_true_dupes / true_dupes
