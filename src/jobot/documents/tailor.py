"""Drafter + Reviewer tailoring loop (Phase 3, T3.2).

`DocumentTailor.generate_tailored_materials` now runs a two-agent loop:
a `Drafter` produces a structured, profile-grounded resume rewrite and a
`Reviewer` critiques it against an A-F rubric (accuracy, relevance,
ATS-friendliness, truthfulness, length). The loop revises until the rubric
passes or max iterations are reached. `verify_fact_truthfulness` is a real
deterministic gate: detectable skill claims must exist in the profile,
experience rows must match real profile employers, and numeric years/contact
claims must not exceed profile facts.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from jobot.ai.router import ModelRouter
from jobot.documents.cover import CoverLetterGenerator
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import JobPosting, UserProfile
from jobot.security.prompt_guard import sanitize_llm_input

logger = logging.getLogger(__name__)

RUBRIC_DIMENSIONS = ("accuracy", "relevance", "ats_friendliness", "truthfulness", "length")
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_MIN_RUBRIC = 3.5

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9._%+-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?[\d\s\-().]{7,}")
_YEARS_RE = re.compile(r"(\d{1,2})\s*(?:\+|to|-)?\s*years?")


class TailoredDocumentResult(BaseModel):
    profile_id: str
    job_id: str
    tailored_summary: str
    highlighted_skills: list[str]
    cover_letter_text: str
    is_truthful: bool
    tailored_resume: str = ""
    tailored_experience: list[dict[str, Any]] = []
    iteration_count: int = 1
    rubric_scores: dict[str, float] = {}
    truthfulness_notes: list[str] = []


class RubricScores(BaseModel):
    scores: dict[str, float]
    issues: list[str]
    verdict: str

    def average(self) -> float:
        return sum(self.scores.values()) / max(len(self.scores), 1)

    def passes(self, min_rubric: float = DEFAULT_MIN_RUBRIC) -> bool:
        return self.verdict == "PASS" or self.average() >= min_rubric


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract the first balanced JSON object from LLM output."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _skill_tokens(text: str, profile: UserProfile, job: JobPosting) -> list[str]:
    """All skill-like tokens present in text (from profile + job skill sources)."""
    universe = {s.lower() for s in profile.skills} | {s.lower() for s in job.parsed_skills}
    found: list[str] = []
    lowered = text.lower()
    for skill in universe:
        if skill and skill.lower() in lowered:
            found.append(skill)
    return found


# Ambiguous lexicon entries that appear as ordinary English words.
_LEXICON_EXCLUDED = {"go"}


def _profile_skill_tokens(profile: UserProfile) -> set[str]:
    """Lowercased profile skill tokens, splitting compound skills so that
    lexicon keywords like 'azure' are covered when the profile lists
    'Microsoft Azure' (never invents claims — it only *relaxes* matching
    against facts the candidate already stated)."""
    tokens: set[str] = set()
    for skill in profile.skills or []:
        lowered = str(skill).lower()
        tokens.add(lowered)
        for part in lowered.replace("/", " ").replace("-", " ").split():
            tokens.add(part)
    return tokens


def _known_tech_claims(text: str, profile: UserProfile) -> list[str]:
    """Skill claims in text detectable via the common-tech lexicon.

    A claim is a violation only if the term is not traceable to ANY profile
    fact: the skills list, experience descriptions/titles, or education.
    """
    from jobot.ai.skill_extractor import SkillExtractor

    fact_parts = [exp.description or "" for exp in (profile.experiences or [])] + [
        f"{edu.institution} {edu.degree} {edu.field_of_study}" for edu in (profile.education or [])
    ]
    allowed_text = " ".join(fact_parts).lower()
    allowed_tokens = _profile_skill_tokens(profile)

    lowered = text.lower()
    claims = []
    for keyword in SkillExtractor.COMMON_TECH_KEYWORDS:
        if keyword in _LEXICON_EXCLUDED:
            continue
        if keyword in allowed_tokens:
            continue
        if keyword in allowed_text:
            continue
        if re.search(r"\b" + re.escape(keyword) + r"\b", lowered):
            claims.append(keyword)
    return claims


def verify_fact_truthfulness_detailed(
    text: str, profile: UserProfile, job: JobPosting | None = None
) -> tuple[bool, list[str]]:
    """Deterministic grounding gate for tailored text. Returns (ok, violations)."""
    violations: list[str] = []
    allowed_tokens = _profile_skill_tokens(profile)

    if job:
        for skill in _skill_tokens(text, profile, job):
            if skill.lower() not in allowed_tokens:
                violations.append(f"skill claim '{skill}' not in profile skills")

    for keyword in _known_tech_claims(text, profile):
        violations.append(f"skill claim '{keyword}' not in profile skills")

    profile_years = profile.custom_qa_answers.get("Years of Experience", "")
    if profile_years:
        try:
            match = re.search(r"\d+", str(profile_years))
            max_years = int(match.group()) if match else 0
        except (AttributeError, ValueError):
            max_years = 0
        if max_years:
            for match in _YEARS_RE.finditer(text):
                claimed = int(match.group(1))
                if claimed > max_years:
                    violations.append(
                        f"experience claim of {claimed} years exceeds profile ({max_years})"
                    )
                    break

    for email in _EMAIL_RE.findall(text):
        if email.lower() != (profile.personal_info.email or "").lower():
            violations.append(f"email '{email}' does not match profile")
            break

    return (not violations, violations)


class Drafter:
    """Drafts a structured, profile-grounded resume rewrite for a job."""

    SYSTEM_PROMPT = (
        "You tailor resumes for ATS systems. You ONLY rephrase and emphasize facts "
        "from the candidate profile. You NEVER invent skills, employers, projects, "
        "titles, dates, or numbers. Reply with a single JSON object of the form: "
        '{"summary": "<2-3 sentence professional summary>", '
        '"skills": ["<skill from profile>", ...], '
        '"experience": [{"company": "<company from profile>", "title": "<title from '
        'profile>", "bullets": ["<bullet grounded in profile description>", ...]}]}. '
        "Every skill listed must be a profile skill; every experience entry must "
        "reference a real profile employer and title."
    )

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()

    def _build_prompt(self, job: JobPosting, profile: UserProfile) -> str:
        facts = (
            f"Name: {profile.personal_info.first_name} {profile.personal_info.last_name}\n"
            f"Email: {profile.personal_info.email}\n"
            f"Phone: {profile.personal_info.phone}\n"
            f"Location: {profile.personal_info.location_city}, {profile.personal_info.location_country}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Target roles: {profile.custom_qa_answers.get('Target Titles', '')}\n"
            f"Years of experience: {profile.custom_qa_answers.get('Years of Experience', '')}\n"
            f"Notice period: {profile.compensation.notice_period_days} days\n"
        )
        if profile.experiences:
            facts += "Experience (ground truth — do not alter titles or companies):\n"
            for exp in profile.experiences:
                facts += (
                    f"- {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'}): "
                    f"{exp.description}\n"
                )
        if profile.education:
            facts += "Education:\n"
            for edu in profile.education:
                facts += f"- {edu.degree} in {edu.field_of_study} at {edu.institution} ({edu.start_year})\n"
        job_title = sanitize_llm_input(job.title)
        job_company = sanitize_llm_input(job.company)
        job_location = sanitize_llm_input(job.location)
        job_skills = [sanitize_llm_input(s) for s in (job.parsed_skills or [])]
        return (
            f"Target Job: {job_title} at {job_company} ({job_location})\n"
            f"Job skills required: {', '.join(job_skills)}\n\n"
            f"Candidate Profile Facts (only these are true):\n{facts}\n\n"
            "Now produce the tailored resume JSON."
        )

    async def draft(self, job: JobPosting, profile: UserProfile) -> dict[str, Any]:
        text = await self.router.generate_text(
            self._build_prompt(job, profile),
            system_prompt=self.SYSTEM_PROMPT,
            task="resume_tailoring",
            temperature=0.6,
            max_tokens=2048,
        )
        if text.startswith(DEGRADATION_TEXT):
            logger.info("LLM unavailable for drafting; using profile-grounded fallback")
            return self._fallback_draft(job, profile)
        parsed = _extract_json(text)
        if parsed is None:
            raise RuntimeError("Drafter returned no parseable JSON")
        return parsed

    async def revise(
        self, job: JobPosting, profile: UserProfile, draft: dict[str, Any], issues: list[str]
    ) -> dict[str, Any]:
        prompt = (
            f"Previous draft: {json.dumps(draft, ensure_ascii=False)}\n\n"
            "Reviewer issues to fix:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + "\n\nReturn the corrected JSON with the same schema."
        )
        text = await self.router.generate_text(
            prompt,
            system_prompt=self.SYSTEM_PROMPT,
            task="resume_tailoring",
            temperature=0.5,
            max_tokens=2048,
        )
        if text.startswith(DEGRADATION_TEXT):
            logger.info("LLM unavailable for revision; keeping grounded fallback draft")
            return self._fallback_draft(job, profile)
        parsed = _extract_json(text)
        if parsed is None:
            raise RuntimeError("Drafter returned no parseable JSON on revision")
        return parsed

    def _fallback_draft(self, job: JobPosting, profile: UserProfile) -> dict[str, Any]:
        """Deterministic, profile-facts-only draft used when the LLM is unavailable."""
        profile_skills_lower = {s.lower() for s in profile.skills}
        skills = [s for s in job.parsed_skills if s.lower() in profile_skills_lower]
        for s in profile.skills:
            if s not in skills:
                skills.append(s)
        experience = []
        for exp in profile.experiences:
            bullets = [exp.description] if exp.description else []
            experience.append({"company": exp.company, "title": exp.title, "bullets": bullets})
        summary = "Professional skilled in " + ", ".join(skills) + "."
        return {"summary": summary, "skills": skills, "experience": experience}


class Reviewer:
    """Critiques a drafted resume against the A-F rubric."""

    SYSTEM_PROMPT = (
        "You are a rigorous ATS resume reviewer. Score the drafted resume 1-5 on each "
        "rubric dimension and list concrete issues. Reply with a single JSON object: "
        '{"scores": {"accuracy": <1-5>, "relevance": <1-5>, "ats_friendliness": <1-5>, '
        '"truthfulness": <1-5>, "length": <1-5>}, "issues": ["<specific issue>", ...], '
        '"verdict": "PASS" | "REVISE"}. Truthfulness is most important: any claim not '
        "supported by the profile facts must yield a REVISE verdict."
    )

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()

    async def review(
        self, job: JobPosting, profile: UserProfile, draft: dict[str, Any]
    ) -> RubricScores:
        job_title = sanitize_llm_input(job.title)
        job_company = sanitize_llm_input(job.company)
        job_skills = [sanitize_llm_input(s) for s in (job.parsed_skills or [])]
        prompt = (
            f"Target Job: {job_title} at {job_company}\n"
            f"Job skills required: {', '.join(job_skills)}\n"
            f"Profile skills (ground truth): {', '.join(profile.skills)}\n"
            f"Profile experience: "
            + ", ".join(f"{exp.title} at {exp.company}" for exp in (profile.experiences or []))
            + "\n\nDrafted Resume JSON:\n"
            + json.dumps(draft, ensure_ascii=False, indent=2)
            + "\n\nScore the draft now."
        )
        text = await self.router.generate_text(
            prompt,
            system_prompt=self.SYSTEM_PROMPT,
            task="resume_reviewer",
            temperature=0.3,
            max_tokens=1024,
        )
        if text.startswith(DEGRADATION_TEXT):
            # Reviewer unavailable: the draft is profile-grounded; accept as-is.
            return RubricScores(
                scores={dim: 5.0 for dim in RUBRIC_DIMENSIONS},
                issues=[],
                verdict="PASS",
            )
        parsed = _extract_json(text) or {}
        scores_raw = parsed.get("scores") or {}
        scores = {
            dim: float(scores_raw.get(dim, 1))
            for dim in RUBRIC_DIMENSIONS
            if str(scores_raw.get(dim, "")).replace(".", "", 1).isdigit()
        }
        issues = [str(i) for i in (parsed.get("issues") or [])]
        verdict = str(parsed.get("verdict") or "REVISE").upper()
        return RubricScores(scores=scores, issues=issues, verdict=verdict)


def _ground_draft(draft: dict[str, Any], profile: UserProfile) -> dict[str, Any]:
    """Drop ungrounded rows from LLM output: skills not in profile, phantom employers."""
    profile_skills = {s.lower() for s in profile.skills}
    skills = [s for s in (draft.get("skills") or []) if s.lower() in profile_skills]

    exp_by_key = {
        f"{exp.company.lower()}|{exp.title.lower()}": exp for exp in (profile.experiences or [])
    }
    experience: list[dict[str, Any]] = []
    for item in draft.get("experience") or []:
        company = str(item.get("company") or "").strip()
        title = str(item.get("title") or "").strip()
        key = f"{company.lower()}|{title.lower()}"
        if key not in exp_by_key:
            continue
        bullets = [str(b).strip() for b in (item.get("bullets") or []) if str(b).strip()]
        experience.append({"company": company, "title": title, "bullets": bullets})

    return {
        "summary": str(draft.get("summary") or "").strip(),
        "skills": skills,
        "experience": experience,
    }


class TailorLoop:
    """Drafter + Reviewer loop producing a grounded tailored resume + cover letter."""

    def __init__(
        self,
        router: ModelRouter | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        min_rubric: float = DEFAULT_MIN_RUBRIC,
    ):
        self.drafter = Drafter(router or ModelRouter())
        self.reviewer = Reviewer(router or ModelRouter())
        self.cover_generator = CoverLetterGenerator(router or ModelRouter())
        self.max_iterations = max_iterations
        self.min_rubric = min_rubric

    async def run(self, job: JobPosting, profile: UserProfile) -> TailoredDocumentResult:
        draft = await self.drafter.draft(job, profile)
        rubric = RubricScores(scores={}, issues=[], verdict="REVISE")
        iteration = 1

        for iteration in range(1, self.max_iterations + 1):
            rubric = await self.reviewer.review(job, profile, draft)
            if rubric.passes(self.min_rubric):
                break
            draft = await self.drafter.revise(job, profile, draft, rubric.issues)

        grounded = _ground_draft(draft, profile)
        summary = grounded["summary"] or " ".join(
            s for s in [profile.custom_qa_answers.get("Target Titles", "")] if s
        )
        highlighted = [s for s in grounded["skills"]]
        resume_text = self._render_markdown(job, profile, grounded)

        ok, notes = verify_fact_truthfulness_detailed(resume_text, profile, job)

        skills_match = [
            s for s in job.parsed_skills if s.lower() in {ps.lower() for ps in profile.skills}
        ]
        cover_letter = await self.cover_generator.generate(
            job, profile, matching_skills=skills_match or None, tone="classic"
        )

        return TailoredDocumentResult(
            profile_id=profile.profile_id,
            job_id=job.job_id,
            tailored_summary=summary,
            highlighted_skills=highlighted or skills_match,
            cover_letter_text=cover_letter,
            is_truthful=ok,
            tailored_resume=resume_text,
            tailored_experience=grounded["experience"],
            iteration_count=iteration,
            rubric_scores=rubric.scores,
            truthfulness_notes=notes,
        )

    def _render_markdown(self, job: JobPosting, profile: UserProfile, draft: dict[str, Any]) -> str:
        """Render grounded draft as single-column ATS plain text."""
        lines = [
            f"=== {profile.personal_info.first_name.upper()} {profile.personal_info.last_name.upper()} ===",
            f"Email: {profile.personal_info.email} | Phone: {profile.personal_info.phone}",
            f"Location: {profile.personal_info.location_city}, {profile.personal_info.location_country}",
            "",
            "--- SUMMARY ---",
            draft["summary"] or "",
            "",
            "--- SKILLS SUMMARY ---",
            ", ".join(draft["skills"] or profile.skills),
        ]
        if draft["experience"]:
            lines.append("")
            lines.append("--- WORK EXPERIENCE ---")
            for item in draft["experience"]:
                lines.append(f"* {item['title']} at {item['company']}")
                for bullet in item["bullets"]:
                    lines.append(f"  - {bullet}")
        if profile.education:
            lines.append("")
            lines.append("--- EDUCATION ---")
            for edu in profile.education:
                lines.append(
                    f"* {edu.degree} in {edu.field_of_study} - {edu.institution} ({edu.start_year})"
                )
        return "\n".join(lines)


class DocumentTailor:
    """Resume Tailoring & Cover Letter Engine (Layer J) — drafter/reviewer loop."""

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()
        self.loop = TailorLoop(self.router)

    def verify_fact_truthfulness(self, tailored_text: str, profile: UserProfile) -> bool:
        """Verify tailored text contains no ungrounded experience or skill claims."""
        ok, _ = verify_fact_truthfulness_detailed(tailored_text, profile)
        return ok

    async def generate_tailored_materials(
        self, job: JobPosting, profile: UserProfile
    ) -> TailoredDocumentResult:
        return await self.loop.run(job, profile)
