"""Candidate Truth System and Grounding Verifier (UC-21).

Enforces zero-hallucination policy for candidate resumes, cover letters, and
form answers by maintaining an immutable/append-only ledger of verified
candidate facts and validating every generated claim against this ground truth.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from jobot.models.domain import CandidateFact, UserProfile
from jobot.storage.db import DatabaseManager

_TOKEN_RE = re.compile(r"\b[A-Za-z0-9+#.-]{2,}\b")
_SPLIT_STMT_RE = re.compile(r"[.\n;]")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_DIGITS_ONLY_RE = re.compile(r"[^\d]")
_NON_DIGIT_SPACE_RE = re.compile(r"[^\d\s]")
_PHONE_10_RE = re.compile(r"\b\d{10,}\b")


class GroundingCheckResult(BaseModel):
    passed: bool
    score: float = 1.0  # 0.0 to 1.0
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    reason: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandidateTruthStore:
    """Repository and query interface over candidate_facts in SQLite."""

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or DatabaseManager()

    def record_fact(
        self,
        fact_type: str,
        fact_value: str,
        profile_id: str = "default",
        source: str = "resume",
        source_path: str | None = None,
        confidence: float = 1.0,
        verified: bool = True,
        verified_by: str | None = "profile_seed",
    ) -> CandidateFact:
        fact = CandidateFact(
            profile_id=profile_id,
            fact_type=fact_type,
            fact_value=fact_value.strip(),
            source=source,
            source_path=source_path,
            confidence=confidence,
            verified=verified,
            verified_at=datetime.now(UTC) if verified else None,
            verified_by=verified_by,
        )
        fact_id = self.db.save_candidate_fact(fact)
        fact.id = fact_id
        return fact

    def get_facts(
        self,
        profile_id: str = "default",
        fact_type: str | None = None,
        verified_only: bool = False,
    ) -> list[CandidateFact]:
        return self.db.list_candidate_facts(
            profile_id=profile_id, fact_type=fact_type, verified_only=verified_only
        )

    def seed_from_profile(self, profile: UserProfile) -> list[CandidateFact]:
        """Extract and persist all factual claims from a UserProfile."""
        facts: list[CandidateFact] = []
        p_id = profile.profile_id or "default"

        # 1. Personal identity facts
        if profile.personal_info.first_name or profile.personal_info.last_name:
            full_name = (
                f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip()
            )
            facts.append(
                self.record_fact("name", full_name, profile_id=p_id, source="user_profile")
            )
        if profile.personal_info.email:
            facts.append(
                self.record_fact(
                    "email", profile.personal_info.email, profile_id=p_id, source="user_profile"
                )
            )
        if profile.personal_info.phone:
            facts.append(
                self.record_fact(
                    "phone", profile.personal_info.phone, profile_id=p_id, source="user_profile"
                )
            )
        if profile.personal_info.location_city:
            loc = profile.personal_info.location_city
            if profile.personal_info.location_state:
                loc += f", {profile.personal_info.location_state}"
            facts.append(self.record_fact("location", loc, profile_id=p_id, source="user_profile"))

        # 2. Skills
        for skill in profile.skills:
            if skill.strip():
                facts.append(
                    self.record_fact("skill", skill.strip(), profile_id=p_id, source="user_profile")
                )

        # 3. Work experiences
        for exp in profile.experiences:
            facts.append(
                self.record_fact("company", exp.company, profile_id=p_id, source="user_profile")
            )
            facts.append(
                self.record_fact("title", exp.title, profile_id=p_id, source="user_profile")
            )
            exp_summary = (
                f"{exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})"
            )
            if exp.description:
                exp_summary += f": {exp.description}"
            facts.append(
                self.record_fact("experience", exp_summary, profile_id=p_id, source="user_profile")
            )
            for tech in exp.technologies:
                if tech.strip():
                    facts.append(
                        self.record_fact(
                            "skill", tech.strip(), profile_id=p_id, source="user_profile"
                        )
                    )

        # 4. Education
        for edu in profile.education:
            edu_summary = f"{edu.degree} in {edu.field_of_study} from {edu.institution} ({edu.start_year}-{edu.end_year or 'Present'})"
            facts.append(
                self.record_fact("education", edu_summary, profile_id=p_id, source="user_profile")
            )
            facts.append(
                self.record_fact(
                    "institution", edu.institution, profile_id=p_id, source="user_profile"
                )
            )
            facts.append(
                self.record_fact("degree", edu.degree, profile_id=p_id, source="user_profile")
            )

        # 5. Compensation
        if profile.compensation.current_ctc_inr is not None:
            facts.append(
                self.record_fact(
                    "current_ctc",
                    str(profile.compensation.current_ctc_inr),
                    profile_id=p_id,
                    source="user_profile",
                )
            )
        if profile.compensation.expected_ctc_inr is not None:
            facts.append(
                self.record_fact(
                    "expected_ctc",
                    str(profile.compensation.expected_ctc_inr),
                    profile_id=p_id,
                    source="user_profile",
                )
            )
        facts.append(
            self.record_fact(
                "notice_period",
                f"{profile.compensation.notice_period_days} days",
                profile_id=p_id,
                source="user_profile",
            )
        )

        return facts


class CandidateGroundingVerifier:
    """Verifies that generated documents or form answers contain zero unsupported claims."""

    def __init__(self, store: CandidateTruthStore | None = None) -> None:
        self.store = store or CandidateTruthStore()

    def verify_text(
        self,
        text: str,
        facts: list[CandidateFact] | None = None,
        profile_id: str = "default",
        strict: bool = True,
    ) -> GroundingCheckResult:
        """Verify text against candidate facts.

        Args:
            text: Text to evaluate (cover letter, tailored resume bullet, form answer)
            facts: Explicit candidate facts (if None, loaded from store for profile_id)
            profile_id: Profile ID to load facts for if facts is None
            strict: If True, any high-confidence unsupported claim fails the check
        """
        if not text.strip():
            return GroundingCheckResult(
                passed=True, score=1.0, reason="Empty text trivially passes"
            )

        if facts is None:
            facts = self.store.get_facts(profile_id=profile_id)

        if not facts:
            return GroundingCheckResult(
                passed=False,
                score=0.0,
                reason="No candidate ground truth facts found in truth store",
            )

        known_tokens = set()
        for f in facts:
            for token in _TOKEN_RE.findall(f.fact_value.lower()):
                known_tokens.add(token)

        # Extract sentences / statements
        statements = [s.strip() for s in _SPLIT_STMT_RE.split(text) if len(s.strip()) > 5]
        supported: list[str] = []
        unsupported: list[str] = []

        # PII / Metric Hallucination Checks:
        # Check for ungrounded emails
        emails_in_text = _EMAIL_RE.findall(text)
        known_emails = {f.fact_value.lower() for f in facts if f.fact_type == "email"}
        for email in emails_in_text:
            if known_emails and email.lower() not in known_emails:
                unsupported.append(f"Ungrounded email address: {email}")

        # Check for ungrounded phone numbers (10+ digits)
        phones_in_text = _PHONE_10_RE.findall(_NON_DIGIT_SPACE_RE.sub("", text))
        known_phones = {
            _DIGITS_ONLY_RE.sub("", f.fact_value) for f in facts if f.fact_type == "phone"
        }
        for phone in phones_in_text:
            if known_phones and phone not in known_phones:
                unsupported.append(f"Ungrounded phone number: {phone}")

        for stmt in statements:
            stmt_tokens = set(_TOKEN_RE.findall(stmt.lower()))
            if not stmt_tokens:
                continue

            overlap = stmt_tokens & known_tokens
            overlap_ratio = len(overlap) / len(stmt_tokens) if stmt_tokens else 0.0

            company_degree_triggers = [
                "bachelor",
                "master",
                "phd",
                "b.tech",
                "m.tech",
                "degree",
                "university",
                "institute",
                "worked at",
                "employed by",
            ]
            has_trigger = any(t in stmt.lower() for t in company_degree_triggers)

            if has_trigger:
                matched_fact = any(
                    f.fact_value.lower() in stmt.lower() or stmt.lower() in f.fact_value.lower()
                    for f in facts
                    if f.fact_type
                    in ("education", "institution", "degree", "company", "experience")
                )
                if matched_fact or overlap_ratio >= 0.3:
                    supported.append(stmt)
                else:
                    unsupported.append(f"Unverified qualification/employer claim: {stmt}")
            elif overlap_ratio >= 0.2:
                supported.append(stmt)
            else:
                if any(char.isdigit() for char in stmt) and len(stmt_tokens) > 4:
                    unsupported.append(f"Unsubstantiated numerical metric: {stmt}")
                elif overlap_ratio == 0.0 and len(stmt_tokens) >= 5:
                    unsupported.append(f"Ungrounded substantive claim: {stmt}")
                else:
                    supported.append(stmt)

        total_checked = len(supported) + len(unsupported)
        score = len(supported) / total_checked if total_checked > 0 else 1.0
        passed = len(unsupported) == 0 if strict else score >= 0.8

        reason = (
            "All claims verified against candidate truth store"
            if passed
            else f"Found {len(unsupported)} ungrounded claim(s)"
        )

        return GroundingCheckResult(
            passed=passed,
            score=round(score, 3),
            supported_claims=supported,
            unsupported_claims=unsupported,
            reason=reason,
        )


__all__ = [
    "CandidateGroundingVerifier",
    "CandidateTruthStore",
    "GroundingCheckResult",
]
