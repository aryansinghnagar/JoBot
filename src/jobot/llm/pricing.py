"""Pricing table loader: package-data YAML with optional user override.

Ships `src/jobot/llm/pricing.yaml`; an optional `~/.jobot/pricing.yaml`
overrides/extends it (e.g., a model JoBot does not know about).
"""

import logging
from pathlib import Path

import yaml

from jobot.llm.base import ProviderPricing

logger = logging.getLogger(__name__)

SHIPPED_PRICING = Path(__file__).resolve().parent / "pricing.yaml"


class PricingTable:
    """Per-provider per-model cost lookup (approximate USD pricing)."""

    def __init__(self) -> None:
        self.providers: dict[str, dict[str, ProviderPricing]] = {}
        self._load_shipped()
        self._load_override()

    def _load_yaml(self, path: Path) -> None:
        if not path.exists():
            return
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for provider, models in raw.items():
            bucket = self.providers.setdefault(str(provider), {})
            for model, price in (models or {}).items():
                if isinstance(price, dict):
                    bucket[str(model)] = ProviderPricing(**price)

    def _load_shipped(self) -> None:
        self._load_yaml(SHIPPED_PRICING)

    def _load_override(self) -> None:
        override = Path.home() / ".jobot" / "pricing.yaml"
        if override.exists():
            logger.debug("Loading pricing override from %s", override)
            self._load_yaml(override)

    def get(self, provider: str, model: str) -> ProviderPricing:
        models = self.providers.get(provider, {})
        if model in models:
            return models[model]
        if "default" in models:
            return models["default"]
        return ProviderPricing()
