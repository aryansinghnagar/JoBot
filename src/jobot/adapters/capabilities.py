"""Adapter Capability Tiers (post-audit safety layer).

Every SiteAdapter subclass declares its capabilities via a class-level
``capabilities`` attribute.  The ``guard_capability`` helper raises
``AdapterCapabilityError`` when an operation is attempted beyond the
adapter's declared tier — preventing simulated adapters from silently
reporting false submission success.
"""

from __future__ import annotations

from enum import Flag, auto


class AdapterCapability(Flag):
    """Bit-flag enum describing what an adapter can *actually* do."""

    DISCOVERY = auto()  # Can discover / list real job postings
    PARSE = auto()  # Can parse real job details from a URL
    FILL_FORM = auto()  # Can map profile data to form fields
    SUBMIT_API = auto()  # Can submit via direct HTTP API
    SUBMIT_BROWSER = auto()  # Can submit via browser automation
    VERIFY = auto()  # Can verify submission externally

    # Convenience composites
    FULL_API = DISCOVERY | PARSE | FILL_FORM | SUBMIT_API | VERIFY
    FULL_BROWSER = DISCOVERY | PARSE | FILL_FORM | SUBMIT_BROWSER | VERIFY
    DISCOVERY_ONLY = DISCOVERY
    DISCOVERY_PARSE = DISCOVERY | PARSE


class AdapterCapabilityError(NotImplementedError):
    """Raised when an adapter operation exceeds its declared capabilities."""

    def __init__(self, adapter_name: str, operation: str, hint: str = "") -> None:
        self.adapter_name = adapter_name
        self.operation = operation
        msg = f"{adapter_name} does not support '{operation}'. This adapter is discovery-only."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)


def guard_capability(
    adapter_name: str,
    capabilities: AdapterCapability,
    required: AdapterCapability,
    operation: str,
    hint: str = "",
) -> None:
    """Raise ``AdapterCapabilityError`` if *required* is not in *capabilities*."""
    if not (capabilities & required):
        raise AdapterCapabilityError(adapter_name, operation, hint)


__all__ = [
    "AdapterCapability",
    "AdapterCapabilityError",
    "guard_capability",
]
