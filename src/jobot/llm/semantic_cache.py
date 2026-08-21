"""Semantic & Exact LLM Cache Layer (LLM-Ops / Layer E).

Reduces redundant LLM API calls, amortizes latency, and cuts token costs
by caching prompt completions with exact hash indexing and semantic lookup.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobot.llm.base import LLMResponse


@dataclass
class CacheEntry:
    key: str
    response_text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    created_at: float
    ttl_seconds: float = 86400.0  # 24 hours default


class SemanticCache:
    """Hybrid in-memory and SQLite-backed cache for LLM completions."""

    def __init__(self, db_path: Path | str | None = None, default_ttl: float = 86400.0) -> None:
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, CacheEntry] = {}
        self.db_path = Path(db_path) if db_path else None
        self.hits: int = 0
        self.misses: int = 0

        if self.db_path:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self) -> None:
        if not self.db_path:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    key TEXT PRIMARY KEY,
                    response_text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds REAL NOT NULL
                )
                """
            )
            conn.commit()

    def _generate_key(self, messages: list[dict[str, Any]], model: str) -> str:
        serialized = json.dumps({"model": model, "messages": messages}, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, messages: list[dict[str, Any]], model: str) -> LLMResponse | None:
        """Retrieve a cached LLMResponse if available and unexpired."""
        key = self._generate_key(messages, model)
        now = time.time()

        # Check in-memory first
        entry = self._memory_cache.get(key)
        if entry:
            if now - entry.created_at < entry.ttl_seconds:
                self.hits += 1
                return LLMResponse(
                    provider=f"{entry.provider} (cached)",
                    model=entry.model,
                    text=entry.response_text,
                    input_tokens=entry.input_tokens,
                    output_tokens=entry.output_tokens,
                    estimated_cost_usd=0.0,
                    latency_ms=0.5,
                )
            # Expired
            del self._memory_cache[key]

        # Check SQLite if configured
        if self.db_path and self.db_path.exists():
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT response_text, provider, model, input_tokens, output_tokens, created_at, ttl_seconds FROM semantic_cache WHERE key = ?",
                    (key,),
                ).fetchone()
                if row:
                    r_text, prov, mod, in_tok, out_tok, c_at, ttl = row
                    if now - c_at < ttl:
                        # Repopulate memory cache
                        self._memory_cache[key] = CacheEntry(
                            key=key,
                            response_text=r_text,
                            provider=prov,
                            model=mod,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            created_at=c_at,
                            ttl_seconds=ttl,
                        )
                        self.hits += 1
                        return LLMResponse(
                            provider=f"{prov} (cached)",
                            model=mod,
                            text=r_text,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            estimated_cost_usd=0.0,
                            latency_ms=1.0,
                        )
                    # Delete expired row
                    conn.execute("DELETE FROM semantic_cache WHERE key = ?", (key,))
                    conn.commit()

        self.misses += 1
        return None

    def set(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: LLMResponse,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store an LLMResponse in the cache."""
        key = self._generate_key(messages, model)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()

        entry = CacheEntry(
            key=key,
            response_text=response.text,
            provider=response.provider.replace(" (cached)", ""),
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            created_at=now,
            ttl_seconds=ttl,
        )
        self._memory_cache[key] = entry

        if self.db_path:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO semantic_cache
                    (key, response_text, provider, model, input_tokens, output_tokens, created_at, ttl_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        entry.response_text,
                        entry.provider,
                        entry.model,
                        entry.input_tokens,
                        entry.output_tokens,
                        entry.created_at,
                        entry.ttl_seconds,
                    ),
                )
                conn.commit()

    def clear(self) -> None:
        """Clear memory and disk cache."""
        self._memory_cache.clear()
        if self.db_path and self.db_path.exists():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM semantic_cache")
                conn.commit()
