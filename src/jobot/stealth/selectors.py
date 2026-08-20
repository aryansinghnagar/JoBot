"""Self-Healing Selector Registry & Locators (UC-10).

Maintains resilient multi-strategy selector chains per portal and ATS platform.
Automatically tries CSS, ARIA role, label, and XPath fallbacks when DOM drift occurs.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SelectorStrategy(BaseModel):
    name: str  # e.g., "primary_id", "aria_label", "xpath", "text_fallback"
    selector: str
    weight: float = 1.0


class FieldSelectorSpec(BaseModel):
    field_name: str  # e.g., "first_name", "email", "resume_upload", "submit_button"
    portal: str  # e.g., "linkedin", "greenhouse", "lever", "naukri", "mock_ats"
    strategies: list[SelectorStrategy] = Field(default_factory=list)


# Pre-configured battle-tested selector registries for major ATS & job boards
DEFAULT_SELECTORS: dict[str, dict[str, list[str]]] = {
    "greenhouse": {
        "first_name": [
            "input#first_name",
            "input[name='first_name']",
            "input[autocomplete='given-name']",
        ],
        "last_name": [
            "input#last_name",
            "input[name='last_name']",
            "input[autocomplete='family-name']",
        ],
        "email": ["input#email", "input[name='email']", "input[type='email']"],
        "phone": ["input#phone", "input[name='phone']", "input[type='tel']"],
        "resume_upload": [
            "input#resume",
            "input[type='file'][name*='resume']",
            "input[type='file']",
        ],
        "cover_letter": ["textarea#cover_letter", "textarea[name='cover_letter']"],
        "submit_button": [
            "button#submit_app",
            "input[type='submit']",
            "button:has-text('Submit Application')",
        ],
    },
    "lever": {
        "full_name": ["input[name='name']", "input#name", "input[autocomplete='name']"],
        "email": ["input[name='email']", "input#email", "input[type='email']"],
        "phone": ["input[name='phone']", "input#phone", "input[type='tel']"],
        "resume_upload": ["input[type='file'][name='resume']", "input[type='file']"],
        "submit_button": [
            "button.template-btn-submit",
            "button:has-text('Submit application')",
            "button[type='submit']",
        ],
    },
    "linkedin": {
        "phone": ["input[id*='phoneNumber']", "input[name*='phoneNumber']", "input[type='tel']"],
        "next_button": [
            "button[aria-label*='Continue to next step']",
            "button:has-text('Next')",
            "button.artdeco-button--primary",
        ],
        "review_button": [
            "button[aria-label*='Review your application']",
            "button:has-text('Review')",
        ],
        "submit_button": [
            "button[aria-label*='Submit application']",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
        ],
    },
    "mock_ats": {
        "name": ["input#name", "input[name='name']"],
        "email": ["input#email", "input[name='email']"],
        "phone": ["input#phone", "input[name='phone']"],
        "resume_upload": ["input#resume", "input[type='file']"],
        "submit_button": ["button#submit-btn", "input[type='submit']", "button:has-text('Submit')"],
    },
}


class SelectorRegistry:
    """Registry managing resilient selector resolution and drift logging."""

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, list[SelectorStrategy]]] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        for portal, fields in DEFAULT_SELECTORS.items():
            if portal not in self._registry:
                self._registry[portal] = {}
            for field_name, selectors in fields.items():
                self._registry[portal][field_name] = [
                    SelectorStrategy(name=f"strategy_{idx}", selector=sel, weight=1.0 - (idx * 0.1))
                    for idx, sel in enumerate(selectors)
                ]

    def register(self, portal: str, field_name: str, selectors: list[str]) -> None:
        if portal not in self._registry:
            self._registry[portal] = {}
        self._registry[portal][field_name] = [
            SelectorStrategy(name=f"custom_{idx}", selector=sel, weight=1.0 - (idx * 0.1))
            for idx, sel in enumerate(selectors)
        ]

    def get_selectors(self, portal: str, field_name: str) -> list[str]:
        """Return ordered list of selector candidates for portal and field."""
        portal_map = self._registry.get(portal.lower(), {})
        strategies = portal_map.get(field_name, [])
        if not strategies:
            # Fallback to general CSS heuristics
            return [
                f"input[name='{field_name}']",
                f"input#{field_name}",
                f"[aria-label*='{field_name}']",
            ]
        return [s.selector for s in strategies]

    async def resolve_element(
        self, page: Any, portal: str, field_name: str, timeout_ms: int = 2000
    ) -> tuple[Any | None, str | None]:
        """Attempt to find visible element using selector ladder; returns (locator, successful_selector)."""
        candidates = self.get_selectors(portal, field_name)
        for idx, selector in enumerate(candidates):
            try:
                locator = page.locator(selector)
                if await locator.first.is_visible():
                    if idx > 0:
                        logger.info(
                            "Self-healing: Primary selector failed for %s:%s; healed with fallback %s",
                            portal,
                            field_name,
                            selector,
                        )
                    return locator.first, selector
            except Exception:  # noqa: BLE001, S112 — selector ladder: each candidate is tried in turn, failures are expected and not actionable
                continue
        return None, None


__all__ = [
    "DEFAULT_SELECTORS",
    "FieldSelectorSpec",
    "SelectorRegistry",
    "SelectorStrategy",
]
