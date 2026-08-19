"""OS-keyring secret store (service: ``jobot``).

All API keys and secrets live in the OS keyring (SETUP.md Tier 3) —
never in source, logs, or git. Keys are dotted paths, e.g.
``llm.api_key.gemini``, matching the `jobot config set` CLI.
"""

import logging

import keyring

logger = logging.getLogger(__name__)

SERVICE = "jobot"


def get_secret(key: str) -> str | None:
    try:
        return keyring.get_password(SERVICE, key)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Keyring read failed for %s: %s", key, exc)
        return None


def set_secret(key: str, value: str) -> None:
    keyring.set_password(SERVICE, key, value)


def delete_secret(key: str) -> None:
    try:
        keyring.delete_password(SERVICE, key)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Keyring delete failed for %s: %s", key, exc)


def has_secret(key: str) -> bool:
    return get_secret(key) is not None


def mask(value: str | None) -> str:
    """Mask a secret for display: keep first 4 chars, redact the rest."""
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***"
