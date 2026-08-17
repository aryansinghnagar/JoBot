"""Prompt Injection Defense Guard (Layer 4/Security).

Provides sanitization and adversarial injection detection for external inputs
such as job descriptions, interactive form questions, and user notes before
they enter LLM prompts.
"""

from __future__ import annotations

import re
from typing import List, Tuple

INJECTION_PATTERNS: List[Tuple[str, str]] = [
    (r"ignore\s+(previous|all|the\s+above|prior)\s+instructions?", "[REDACTED_INJECTION_OVERRIDE]"),
    (r"disregard\s+(above|previous|all|prior)\s+(instructions?|rules?|prompts?)", "[REDACTED_INJECTION_DISREGARD]"),
    (r"forget\s+(all\s+)?(rules?|instructions?|prompts?)", "[REDACTED_INJECTION_FORGET]"),
    (r"override\s+(policy|rules?|system|instructions?)", "[REDACTED_INJECTION_OVERRIDE]"),
    (r"new\s+instructions?:", "[REDACTED_INJECTION_NEW_INSTRUCTIONS]"),
    (r"you\s+are\s+now\s+(a|an)?", "[REDACTED_INJECTION_ROLE]"),
    (r"act\s+as\s+(a|an)?", "[REDACTED_INJECTION_ROLE]"),
    (r"pretend\s+(to\s+be|you\s+are)", "[REDACTED_INJECTION_ROLE]"),
    (r"reveal\s+(your\s+)?(system\s+prompt|instructions?|hidden\s+rules?)", "[REDACTED_INJECTION_LEAKAGE]"),
    (r"output\s+(your\s+)?(system\s+prompt|initial\s+prompt)", "[REDACTED_INJECTION_LEAKAGE]"),
    (r"(print|show|display|reveal|output|dump|leak)\s+(your\s+|the\s+)?(system\s+prompt|initial\s+prompt)", "[REDACTED_INJECTION_LEAKAGE]"),
    (r"system\s+prompt", "[REDACTED_INJECTION_SYSTEM_PROMPT]"),
    (r"<\/?(system|instruction|prompt|admin|developer|assistant)>", "[REDACTED_INJECTION_TAG]"),
    (r"\[(SYSTEM|INSTRUCTION|DEVELOPER|ADMIN)\]", "[REDACTED_INJECTION_TAG]"),
]


def contains_prompt_injection(text: str) -> bool:
    """Check if the text contains any known prompt injection patterns."""
    if not text:
        return False
    for pattern, _ in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def find_prompt_injections(text: str) -> List[str]:
    """Return all detected injection match strings from text."""
    if not text:
        return []
    matches: List[str] = []
    for pattern, _ in INJECTION_PATTERNS:
        found = re.findall(pattern, text, flags=re.IGNORECASE)
        if found:
            matches.extend(str(m) for m in found)
    return matches


def sanitize_llm_input(text: str) -> str:
    """Sanitize external untrusted text before interpolation into LLM prompts."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


__all__ = [
    "INJECTION_PATTERNS",
    "contains_prompt_injection",
    "find_prompt_injections",
    "sanitize_llm_input",
]
