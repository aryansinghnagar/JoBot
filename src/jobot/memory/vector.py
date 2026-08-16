import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VectorPoint(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VectorMemory:
    """
    Local Vector Memory Engine (Phase 4.2).
    Provides localized semantic search and RAG retrieval over past successful Q&A answers,
    user corrections, and resume bullet relevance scores.
    """

    def __init__(self, collection_name: str = "successful_answers") -> None:
        self.collection_name = collection_name
        self._points: List[VectorPoint] = []

    def _simple_embedding(self, text: str, dim: int = 16) -> List[float]:
        """Generate deterministic local pseudo-embedding vector for text."""
        vec = [0.0] * dim
        words = text.lower().split()
        for i, word in enumerate(words):
            val = sum(ord(c) for c in word)
            vec[i % dim] += math.sin(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def store_answer(
        self, point_id: str, question: str, answer: str, site: str = "general"
    ) -> None:
        """Store Q&A pair vector point."""
        text = f"Q: {question} A: {answer}"
        vec = self._simple_embedding(text)
        point = VectorPoint(
            id=point_id,
            vector=vec,
            payload={"question": question, "answer": answer, "site": site},
        )
        self._points.append(point)

    def retrieve_similar(
        self, query_text: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve most similar stored Q&A answers via cosine similarity."""
        if not self._points:
            return []

        query_vec = self._simple_embedding(query_text)
        scored_points = []
        for p in self._points:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_vec, p.vector))
            scored_points.append((dot, p.payload))

        scored_points.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_points[:top_k]]
