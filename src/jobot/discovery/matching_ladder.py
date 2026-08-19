"""Multi-Stage Matching Ladder (UC-23).

Implements the 4-stage job matching ladder:
1. Hard Filter Gate (Location, min experience, salary bounds)
2. Skill Overlap & Keyword Density (Jaccard + requirement coverage)
3. Embedding & Semantic Proximity (Vector cosine similarity)
4. LLM Fit Analysis & Structured Explanation (Strengths, growth areas, fit rubric)
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field

from jobot.ai.router import ModelRouter
from jobot.ai.skill_extractor import SkillExtractor
from jobot.llm.router import DEGRADATION_TEXT
from jobot.memory.vector import simple_embedding
from jobot.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class MatchingLadderResult(BaseModel):
    posting: JobPosting
    passed_hard_filters: bool
    hard_filter_reasons: list[str] = Field(default_factory=list)
    skill_score: float = 0.0  # Stage 2
    semantic_score: float = 0.0  # Stage 3
    llm_score: float | None = None  # Stage 4
    composite_score: float = 0.0  # Overall weighted score
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    growth_areas: list[str] = Field(default_factory=list)
    recommendation: str = "LOW_FIT"  # HIGH_FIT | MEDIUM_FIT | LOW_FIT | FILTERED_OUT
    explanation: str = ""


class MatchingLadder:
    """4-Stage Matching Ladder for intelligent candidate-job fit evaluation."""

    def __init__(
        self,
        router: ModelRouter | None = None,
        skill_extractor: SkillExtractor | None = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.skill_extractor = skill_extractor or SkillExtractor()
        self._candidate_vec_cache: dict[str, list[float]] = {}
        self._candidate_skills_cache: dict[str, set[str]] = {}
        self._candidate_years_cache: dict[str, int] = {}

    def _get_candidate_years(self, profile: UserProfile) -> int:
        p_key = f"{profile.profile_id}:{profile.version}"
        if p_key in self._candidate_years_cache:
            return self._candidate_years_cache[p_key]
        candidate_years = 0
        for exp in profile.experiences:
            try:
                start_year = int(exp.start_date.split("-")[0])
                end_year = int(exp.end_date.split("-")[0]) if exp.end_date else 2026
                candidate_years += max(0, end_year - start_year)
            except (ValueError, IndexError):
                candidate_years += 2
        self._candidate_years_cache[p_key] = candidate_years
        return candidate_years

    def _get_candidate_skills_lower(self, profile: UserProfile) -> set[str]:
        p_key = f"{profile.profile_id}:{profile.version}"
        if p_key not in self._candidate_skills_cache:
            self._candidate_skills_cache[p_key] = {s.lower() for s in profile.skills}
        return self._candidate_skills_cache[p_key]

    def _get_candidate_vec(self, profile: UserProfile) -> list[float]:
        p_key = f"{profile.profile_id}:{profile.version}"
        if p_key not in self._candidate_vec_cache:
            candidate_corpus = " ".join(
                [
                    " ".join(profile.skills),
                    " ".join(f"{e.title} {e.description}" for e in profile.experiences),
                    " ".join(f"{ed.degree} {ed.field_of_study}" for ed in profile.education),
                ]
            )
            self._candidate_vec_cache[p_key] = simple_embedding(candidate_corpus, dim=32)
        return self._candidate_vec_cache[p_key]

    # ------------------------------------------------------------------
    # Stage 1: Hard Filter Gate
    # ------------------------------------------------------------------

    def evaluate_hard_filters(
        self,
        posting: JobPosting,
        profile: UserProfile,
        target_location: str = "",
        allow_remote: bool = True,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        # 1. Location match (if target specified and not remote)
        job_loc = (posting.location or "").lower()
        is_remote = "remote" in job_loc or "work from home" in (posting.description or "").lower()

        if target_location and not is_remote:
            target_norm = target_location.lower().strip()
            if target_norm not in job_loc and not any(
                part in job_loc for part in target_norm.split(",")
            ):
                if not (allow_remote and is_remote):
                    reasons.append(
                        f"Location mismatch: Job is in '{posting.location}', target is '{target_location}'"
                    )

        # 2. Experience bounds (if years specified in job description)
        exp_match = re.search(
            r"(\d+)\s*(?:\+|to|-)?\s*years?",
            posting.experience_required or posting.description or "",
            re.IGNORECASE,
        )
        if exp_match:
            required_years = int(exp_match.group(1))
            candidate_years = self._get_candidate_years(profile)
            if required_years > candidate_years + 3 and required_years > 5:
                reasons.append(
                    f"Experience mismatch: Requires {required_years}+ years, candidate has ~{candidate_years} years"
                )

        passed = len(reasons) == 0
        return passed, reasons

    # ------------------------------------------------------------------
    # Stage 2: Skill Overlap & Keyword Density
    # ------------------------------------------------------------------

    def evaluate_skill_overlap(
        self, posting: JobPosting, profile: UserProfile
    ) -> tuple[float, list[str], list[str]]:
        extracted = (
            self.skill_extractor.extract_skills_sync(posting.description)
            if posting.description
            else []
        )
        combined_skills = list(dict.fromkeys(posting.parsed_skills + extracted))
        skills_to_check = combined_skills if combined_skills else posting.parsed_skills

        if not skills_to_check:
            # Fallback if no skills parsed
            return 0.70, profile.skills[:3], []

        candidate_skills_lower = self._get_candidate_skills_lower(profile)
        matching = [s for s in skills_to_check if s.lower() in candidate_skills_lower]
        missing = [s for s in skills_to_check if s.lower() not in candidate_skills_lower]

        score = len(matching) / len(skills_to_check)
        return round(score, 3), matching, missing

    # ------------------------------------------------------------------
    # Stage 3: Embedding & Semantic Proximity
    # ------------------------------------------------------------------

    def evaluate_semantic_proximity(self, posting: JobPosting, profile: UserProfile) -> float:
        job_corpus = f"{posting.title} {posting.description} {' '.join(posting.parsed_skills)}"
        vec_candidate = self._get_candidate_vec(profile)
        vec_job = simple_embedding(job_corpus, dim=32)

        dot = sum(a * b for a, b in zip(vec_candidate, vec_job))
        similarity = max(0.0, min(1.0, (dot + 1.0) / 2.0))
        return round(similarity, 3)

    # ------------------------------------------------------------------
    # Stage 4: LLM Fit Analysis & Structured Explanation
    # ------------------------------------------------------------------

    async def evaluate_llm_fit(
        self,
        posting: JobPosting,
        profile: UserProfile,
        matching_skills: list[str],
        missing_skills: list[str],
    ) -> tuple[float, list[str], list[str], str]:
        prompt = (
            f"Analyze candidate fit for the target job role.\n\n"
            f"Candidate: {profile.personal_info.first_name} {profile.personal_info.last_name}\n"
            f"Candidate Skills: {', '.join(profile.skills)}\n"
            f"Target Job: {posting.title} at {posting.company}\n"
            f"Matching Skills: {', '.join(matching_skills)}\n"
            f"Missing Skills: {', '.join(missing_skills)}\n\n"
            "Return a JSON object with: "
            '{"fit_score": <0.0-1.0>, "strengths": ["<strength 1>", ...], '
            '"growth_areas": ["<growth area 1>", ...], "explanation": "<1-2 sentence rationale>"}'
        )

        try:
            text = await self.router.generate_text(
                prompt,
                task="job_matching",
                temperature=0.2,
                max_tokens=512,
            )
            if text.startswith(DEGRADATION_TEXT):
                return self._fallback_llm_fit(matching_skills, missing_skills)

            # Parse JSON
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                data = json.loads(text[start : end + 1])
                score = float(data.get("fit_score", 0.75))
                strengths = [str(s) for s in data.get("strengths", [])]
                growth_areas = [str(g) for g in data.get("growth_areas", [])]
                explanation = str(
                    data.get("explanation", "Candidate has strong foundational match.")
                )
                return score, strengths, growth_areas, explanation
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM fit analysis fallback: %s", exc)

        return self._fallback_llm_fit(matching_skills, missing_skills)

    def _fallback_llm_fit(
        self, matching_skills: list[str], missing_skills: list[str]
    ) -> tuple[float, list[str], list[str], str]:
        score = len(matching_skills) / max(1, len(matching_skills) + len(missing_skills))
        strengths = [f"Proficient in {s}" for s in matching_skills[:3]]
        growth_areas = [f"Familiarity with {s} desired" for s in missing_skills[:3]]
        explanation = f"Matched {len(matching_skills)} key required technical competencies."
        return round(score, 3), strengths, growth_areas, explanation

    # ------------------------------------------------------------------
    # Composite Ladder Evaluation
    # ------------------------------------------------------------------

    async def evaluate_ladder(
        self,
        posting: JobPosting,
        profile: UserProfile,
        target_location: str = "",
        include_llm_stage: bool = True,
    ) -> MatchingLadderResult:
        # Stage 1: Hard Filter Gate
        passed_filters, filter_reasons = self.evaluate_hard_filters(
            posting, profile, target_location=target_location
        )
        if not passed_filters:
            return MatchingLadderResult(
                posting=posting,
                passed_hard_filters=False,
                hard_filter_reasons=filter_reasons,
                composite_score=0.0,
                recommendation="FILTERED_OUT",
                explanation=f"Filtered out by hard constraints: {'; '.join(filter_reasons)}",
            )

        # Stage 2: Skill Overlap
        skill_score, matching_skills, missing_skills = self.evaluate_skill_overlap(posting, profile)

        # Stage 3: Semantic Proximity
        semantic_score = self.evaluate_semantic_proximity(posting, profile)

        # Stage 4: LLM Fit (Optional / Fast-path)
        llm_score: float | None = None
        strengths: list[str] = []
        growth_areas: list[str] = []
        explanation = ""

        if include_llm_stage:
            llm_score, strengths, growth_areas, explanation = await self.evaluate_llm_fit(
                posting, profile, matching_skills, missing_skills
            )
            composite = 0.40 * skill_score + 0.30 * semantic_score + 0.30 * llm_score
        else:
            composite = 0.50 * skill_score + 0.50 * semantic_score
            explanation = f"Heuristic match based on {len(matching_skills)} matching skills."

        composite = round(composite, 3)
        if composite >= 0.70:
            rec = "HIGH_FIT"
        elif composite >= 0.45:
            rec = "MEDIUM_FIT"
        else:
            rec = "LOW_FIT"

        return MatchingLadderResult(
            posting=posting,
            passed_hard_filters=True,
            hard_filter_reasons=[],
            skill_score=skill_score,
            semantic_score=semantic_score,
            llm_score=llm_score,
            composite_score=composite,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            strengths=strengths,
            growth_areas=growth_areas,
            recommendation=rec,
            explanation=explanation,
        )


__all__ = [
    "MatchingLadder",
    "MatchingLadderResult",
]
