import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    memory_id: str
    tier: str
    key: str
    content: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EightTierMemorySystem:
    """
    8-Tier Memory System (Layer E).
    Manages Working, Episodic, Semantic, Procedural, LongTerm, Temporal, Consolidated, and Audit memory.
    """

    def __init__(self) -> None:
        self.working_memory: Dict[str, Any] = {}
        self.episodic_memory: List[MemoryRecord] = []
        self.semantic_memory: Dict[str, Any] = {}
        self.procedural_memory: Dict[str, Any] = {}
        self.long_term_memory: List[MemoryRecord] = []
        self.temporal_memory: List[MemoryRecord] = []
        self.consolidated_memory: Dict[str, Any] = {}
        self.audit_memory: List[MemoryRecord] = []

    def set_working_memory(self, key: str, value: Any) -> None:
        self.working_memory[key] = value

    def add_episodic_record(self, key: str, content: Dict[str, Any]) -> MemoryRecord:
        rec = MemoryRecord(
            memory_id=f"EP-{len(self.episodic_memory)+1}",
            tier="episodic",
            key=key,
            content=content,
        )
        self.episodic_memory.append(rec)
        return rec

    def add_audit_record(self, key: str, content: Dict[str, Any]) -> MemoryRecord:
        rec = MemoryRecord(
            memory_id=f"AUD-{len(self.audit_memory)+1}",
            tier="audit",
            key=key,
            content=content,
        )
        self.audit_memory.append(rec)
        return rec

    def search_semantic(self, keyword: str) -> List[Any]:
        results = []
        for k, v in self.semantic_memory.items():
            if keyword.lower() in k.lower() or keyword.lower() in str(v).lower():
                results.append(v)
        return results
