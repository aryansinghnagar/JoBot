"""Salary benchmarking: shipped YAML reference data, live sources opt-in."""

import json
import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from jobot.security.url_guard import safe_urlopen
from jobot.stealth.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
LIVE_ENV = "JOBOT_RUN_LIVE_SALARY"

_AMOUNT_RE = re.compile(r"(?:[A-Z]{3}\s*)?([0-9]{2,3}[,0-9]{2,3})(?:\s*(?:k|K|/yr|per year))?")


class SalaryBand(BaseModel):
    role: str
    region: str
    currency: str
    p25: int
    p50: int
    p75: int
    source: str


class SalaryBenchmarker:
    """Looks up salary bands per role+region.

    Default source is shipped YAML reference data (approximate, labeled).
    When `JOBOT_RUN_LIVE_SALARY=1` and the circuit is closed, a best-effort
    live fetch is attempted first (24h cache); any failure falls back to the
    YAML band silently — live data is never fabricated.
    """

    def __init__(
        self,
        data_path: Path | None = None,
        cache_path: Path | None = None,
        http_getter: Callable[[str], tuple[int, str]] | None = None,
        breaker: CircuitBreaker | None = None,
        cache_ttl_seconds: int = 24 * 3600,
    ) -> None:
        self.data_path = Path(data_path or (DATA_DIR / "salaries.yaml"))
        cache_dir = Path(cache_path) if cache_path else (Path.home() / ".jobot" / "data")
        self.cache_path = cache_dir / "salary_cache.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.http_getter = http_getter
        self.breaker = breaker or CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        self.breaker_domain = "salary_live"
        self.cache_ttl_seconds = cache_ttl_seconds
        self._yaml: dict[str, Any] | None = None

    def _load_yaml(self) -> dict[str, Any]:
        if self._yaml is None:
            self._yaml = yaml.safe_load(self.data_path.read_text(encoding="utf-8")) or {}
        return self._yaml

    def yaml_lookup(self, role: str, region: str, currency: str) -> SalaryBand | None:
        entry = self._load_yaml().get("roles", {}).get(role, {}).get(region)
        if not entry:
            return None
        return SalaryBand(
            role=role,
            region=region,
            currency=str(entry.get("currency", currency)),
            p25=int(entry["p25"]),
            p50=int(entry["p50"]),
            p75=int(entry["p75"]),
            source="local benchmark data (approximate)",
        )

    def list_roles(self) -> list[str]:
        return list(self._load_yaml().get("roles", {}).keys())

    def _cache_get(self, key: str) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        item: dict[str, Any] | None = data.get(key)
        if not item:
            return None
        if time.time() - item.get("ts", 0) > self.cache_ttl_seconds:
            return None
        return item

    def _cache_set(self, key: str, payload: dict[str, Any]) -> None:
        data: dict[str, Any] = {}
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data[key] = {"ts": time.time(), "payload": payload}
        self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _fetch_live(self, role: str, region: str) -> SalaryBand | None:
        """Best-effort levels.fyi page fetch + amount extraction. Never fabricates."""
        slug = role.replace("_", "-").lower()
        url = f"https://www.levels.fyi/companies/{slug}/salaries"
        getter = self.http_getter or self._default_getter
        try:
            status, html = getter(url)
            if status != 200 or not html:
                return None
            amounts = []
            for match in _AMOUNT_RE.findall(html):
                try:
                    amounts.append(int(match.replace(",", "")))
                except ValueError:
                    continue
            if len(amounts) < 3:
                return None
            amounts.sort()
            mid = len(amounts) // 2
            return SalaryBand(
                role=role,
                region=region,
                currency="USD",
                p25=amounts[len(amounts) // 4],
                p50=amounts[mid],
                p75=amounts[(3 * len(amounts)) // 4],
                source="live levels.fyi fetch (best-effort)",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("salary live fetch failed for %s: %s", role, exc)
            return None

    @staticmethod
    def _default_getter(url: str) -> tuple[int, str]:
        with safe_urlopen(url, timeout=15.0) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")

    def benchmark(
        self,
        role: str,
        region: str = "India",
        currency: str = "INR",
    ) -> SalaryBand | None:
        yaml_band = self.yaml_lookup(role, region, currency)
        if not yaml_band:
            return None

        if os.getenv(LIVE_ENV) == "1" and self.breaker.get_state(self.breaker_domain) != "OPEN":
            key = f"{role}|{region}"
            cached = self._cache_get(key)
            if cached:
                return SalaryBand(**cached["payload"])
            live = self._fetch_live(role, region)
            if live is not None:
                self.breaker.record_success(self.breaker_domain)
                self._cache_set(key, live.model_dump())
                return live
            self.breaker.record_failure(self.breaker_domain)

        return yaml_band
