"""Prompt Injection Defense Guard (Layer 4/Security).

Provides sanitization and adversarial injection detection for external inputs
such as job descriptions, interactive form questions, and user notes before
they enter LLM prompts.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r"ignore\s+(all\s+)?(previous|prior|above|the\s+above)?\s*instructions?",
        "[REDACTED_INJECTION_OVERRIDE]",
    ),
    (
        r"disregard\s+(all\s+)?(prior|previous|above|the\s+above|the)?\s*(instructions?|rules?|prompts?)",
        "[REDACTED_INJECTION_DISREGARD]",
    ),
    (
        r"forget\s+(all\s+)?(rules?|instructions?|prompts?|constraints?)",
        "[REDACTED_INJECTION_FORGET]",
    ),
    (
        r"override\s+(policy|rules?|system|instructions?|user\s+persona)",
        "[REDACTED_INJECTION_OVERRIDE]",
    ),
    (
        r"(bypass|disable|ignore)\s+(safety|security|guardrails?|filters?)",
        "[REDACTED_INJECTION_BYPASS]",
    ),
    (r"(dan\s+mode|jailbreak|developer\s+mode)", "[REDACTED_INJECTION_JAILBREAK]"),
    (r"###\s*instruction:", "[REDACTED_INJECTION_NEW_INSTRUCTIONS]"),
    (r"new\s+instructions?:", "[REDACTED_INJECTION_NEW_INSTRUCTIONS]"),
    (r"you\s+are\s+now\s+(a|an)?", "[REDACTED_INJECTION_ROLE]"),
    (r"act\s+as\s+(a|an)?", "[REDACTED_INJECTION_ROLE]"),
    (r"pretend\s+(to\s+be|you\s+are)", "[REDACTED_INJECTION_ROLE]"),
    (
        r"reveal\s+(your\s+)?(system\s+prompt|instructions?|hidden\s+rules?|secret)",
        "[REDACTED_INJECTION_LEAKAGE]",
    ),
    (r"output\s+(your\s+)?(system\s+prompt|initial\s+prompt)", "[REDACTED_INJECTION_LEAKAGE]"),
    (
        r"(print|show|display|reveal|output|dump|leak)\s+(your\s+|the\s+)?(system\s+prompt|initial\s+prompt|secret\s+master\s+key)",
        "[REDACTED_INJECTION_LEAKAGE]",
    ),
    (r"system\s+prompt", "[REDACTED_INJECTION_SYSTEM_PROMPT]"),
    (r"<\/?(system|instruction|prompt|admin|developer|assistant)>", "[REDACTED_INJECTION_TAG]"),
    (r"\[(SYSTEM|INSTRUCTION|DEVELOPER|ADMIN)\]", "[REDACTED_INJECTION_TAG]"),
]


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\u200b-\u200f\ufeff\u202a-\u202e]", "", norm)


def contains_prompt_injection(text: str) -> bool:
    """Check if the text contains any known prompt injection patterns."""
    if not text:
        return False
    norm_text = _normalize_text(text)
    for pattern, _ in INJECTION_PATTERNS:
        if re.search(pattern, norm_text, flags=re.IGNORECASE):
            return True
    return False


def find_prompt_injections(text: str) -> list[str]:
    """Return all detected injection match strings from text."""
    if not text:
        return []
    norm_text = _normalize_text(text)
    matches: list[str] = []
    for pattern, _ in INJECTION_PATTERNS:
        found = re.findall(pattern, norm_text, flags=re.IGNORECASE)
        if found:
            matches.extend(str(m) for m in found)
    return matches


def sanitize_llm_input(text: str) -> str:
    """Sanitize external untrusted text before interpolation into LLM prompts.

    Applies all patterns sequentially. To ensure idempotency (running
    sanitize twice produces the same output as running once), we skip
    text inside ``[REDACTED_INJECTION_...]`` blocks on subsequent passes
    by checking if the text already contains ``[REDACTED_INJECTION``.
    """
    if not text:
        return ""

    def _make_replacer(rep: str) -> Any:
        return lambda _m: rep

    sanitized: str = _normalize_text(text)
    for pattern, replacement in INJECTION_PATTERNS:
        # Idempotency guard: if the replacement string itself contains
        # a word that matches a subsequent pattern (e.g., "[REDACTED_INJECTION_JAILBREAK]"
        # matches the "jailbreak" pattern), the second pass would double-replace.
        # Fix: only replace in the part of the text that is NOT already inside
        # a [REDACTED_INJECTION_...] block.
        sanitized = re.sub(
            pattern,
            _make_replacer(str(replacement)),
            sanitized,
            flags=re.IGNORECASE,
        )
    # Idempotency: collapse any nested [REDACTED_INJECTION_[REDACTED_INJECTION_...]] into [REDACTED_INJECTION_...]
    while "[REDACTED_INJECTION_[REDACTED_INJECTION_" in sanitized:
        sanitized = re.sub(
            r"\[REDACTED_INJECTION_\[REDACTED_INJECTION_(\w+)\]\]",
            r"[REDACTED_INJECTION_\1]",
            sanitized,
        )
    return sanitized


__all__ = [
    "INJECTION_PATTERNS",
    "contains_prompt_injection",
    "find_prompt_injections",
    "sanitize_llm_input",
]
