"""ATS parseability scoring (Phase 3, T3.1).

Deterministic, LLM-free scoring of extracted PDF text: contact presence,
section coverage, single-column layout, char density, bullet usage, and
length. Operates on extracted text only, so pdftotext and pdfminer.six
extractors score identically-shaped documents the same way.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

ATS_PASS_THRESHOLD = 0.85

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SECTION_HEADER_RE = re.compile(
    r"^(SUMMARY|SKILLS|WORK EXPERIENCE|EXPERIENCE|EDUCATION|PROJECTS|CERTIFICATIONS)\s*(SUMMARY)?$",
    re.IGNORECASE,
)
_BULLET_LINE_RE = re.compile(r"^\s*([\u2022\u2013\-*o])\s+")


class AtsScore(BaseModel):
    score: float
    passed: bool
    threshold: float
    details: Dict[str, Any]


def extract_pdf_text_pdftotext(path: Path) -> str:
    """Extract text via poppler's pdftotext -layout (best fidelity)."""
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not found on PATH")
    result = subprocess.run(
        [exe, "-layout", str(path), "-"], capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr[:500]}")
    return result.stdout


def extract_pdf_text_pdfminer(path: Path) -> str:
    """Extract text via pdfminer.six (pure-python fallback)."""
    from pdfminer.high_level import extract_text

    return extract_text(str(path))


def extract_pdf_text(path: Path, prefer: str = "auto") -> str:
    """Extract PDF text; auto prefers pdftotext when available."""
    if prefer == "pdftotext" or (prefer == "auto" and shutil.which("pdftotext")):
        try:
            return extract_pdf_text_pdftotext(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("pdftotext extraction failed (%s); using pdfminer", exc)
    return extract_pdf_text_pdfminer(path)


class AtsScorer:
    """Scores extracted resume text for ATS parseability."""

    def _count_section_headers(self, text: str) -> int:
        headers = set()
        for line in text.splitlines():
            stripped = line.strip().rstrip(":").strip()
            if _SECTION_HEADER_RE.match(stripped):
                headers.add(stripped.upper())
        return len(headers)

    def _multi_column_lines(self, text: str) -> tuple[int, int]:
        """Count lines that look like multi-column output (>=2 wide gaps)."""
        total = 0
        multi = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            total += 1
            gaps = len(re.findall(r" {4,}", line))
            if gaps >= 2:
                multi += 1
        return multi, total

    def score_text(self, text: str) -> AtsScore:
        details: Dict[str, Any] = {}
        total_chars = max(len(text), 1)
        non_ws = len(text) - len(re.sub(r"\s", "", text))
        density = non_ws / total_chars

        multi, total = self._multi_column_lines(text)
        col_ratio = multi / total if total else 0.0

        bullets = sum(1 for line in text.splitlines() if _BULLET_LINE_RE.match(line))

        checks = {
            "email": bool(_EMAIL_RE.search(text)),
            "section_headers": self._count_section_headers(text),
            "multi_column_ratio": round(col_ratio, 4),
            "char_density": round(density, 4),
            "bullets": bullets,
            "length": len(text),
        }
        details.update(checks)

        passed = {
            "email": checks["email"],
            "section_headers": checks["section_headers"] >= 3,
            "single_column": checks["multi_column_ratio"] < 0.05,
            "char_density": 0.15 <= density <= 0.95,
            "bullets": bullets >= 2,
            "length": 400 <= len(text) <= 20000,
        }

        weights = {
            "email": 0.15,
            "section_headers": 0.25,
            "single_column": 0.15,
            "char_density": 0.15,
            "bullets": 0.15,
            "length": 0.15,
        }
        score = sum(weights[k] for k, ok in passed.items() if ok)
        details["passed_checks"] = passed
        return AtsScore(
            score=round(score, 3),
            passed=score >= ATS_PASS_THRESHOLD,
            threshold=ATS_PASS_THRESHOLD,
            details=details,
        )

    def score_pdf(self, path: Path, prefer: str = "auto") -> AtsScore:
        text = extract_pdf_text(path, prefer=prefer)
        return self.score_text(text)


def score_pdf_file(path: Path, prefer: str = "auto") -> AtsScore:
    return AtsScorer().score_pdf(path, prefer=prefer)
