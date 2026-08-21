"""Skill-gap analysis: demand from saved job postings vs candidate profile."""

import asyncio
import json
from collections import Counter

from pydantic import BaseModel

from jobot.ai.skill_extractor import SkillExtractor
from jobot.llm.router import DEGRADATION_TEXT, ModelRouter
from jobot.models.domain import UserProfile
from jobot.storage.db import DatabaseManager


class SkillGap(BaseModel):
    skill: str
    demand_count: int
    in_profile: bool


class SkillDemand(BaseModel):
    skill: str
    count: int


class SkillGapReport(BaseModel):
    total_postings: int
    profile_skills: list[str]
    top_demanded: list[SkillDemand]
    gaps: list[SkillGap]
    recommendations: list[str]
    sourced_from: str


def _rule_based_recommendations(gaps: list[SkillGap], cap: int = 6) -> list[str]:
    out = []
    for gap in gaps[:cap]:
        out.append(
            f"Learn/strengthen '{gap.skill}' (demanded by {gap.demand_count} saved posting(s))."
        )
    return out


class SkillGapAnalyzer:
    """Aggregates skills demanded across saved postings and diffs vs the profile."""

    def __init__(
        self,
        db: DatabaseManager | None = None,
        extractor: SkillExtractor | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.db = db or DatabaseManager()
        self.extractor = extractor or SkillExtractor(router=router or ModelRouter())
        self.router = router or self.extractor.router

    def analyze(self, profile: UserProfile, limit: int = 500) -> SkillGapReport:
        postings = self.db.list_job_postings(limit=limit)
        counter: Counter[str] = Counter()
        parsed_missing = 0
        for posting in postings:
            skills = [s.lower() for s in (posting.parsed_skills or [])]
            if not skills and posting.description:
                try:
                    skills = [
                        s.lower() for s in self.extractor.extract_skills_sync(posting.description)
                    ]
                    parsed_missing += 1
                except Exception:  # noqa: BLE001
                    skills = []
            for s in skills:
                if s:
                    counter[s] += 1

        profile_set = {s.lower() for s in profile.skills}
        gaps = [
            SkillGap(skill=skill, demand_count=count, in_profile=skill in profile_set)
            for skill, count in counter.most_common()
            if skill not in profile_set
        ]
        top_demanded = [SkillDemand(skill=s, count=c) for s, c in counter.most_common(10)]
        recommendations = self._recommend(profile, gaps)
        return SkillGapReport(
            total_postings=len(postings),
            profile_skills=list(profile.skills),
            top_demanded=top_demanded,
            gaps=gaps,
            recommendations=recommendations,
            sourced_from="saved postings"
            + (f" (incl. {parsed_missing} parsed on demand)" if parsed_missing else ""),
        )

    async def analyze_async(self, profile: UserProfile, limit: int = 500) -> SkillGapReport:
        postings = self.db.list_job_postings(limit=limit)
        counter: Counter[str] = Counter()
        parsed_missing = 0
        for posting in postings:
            skills = [s.lower() for s in (posting.parsed_skills or [])]
            if not skills and posting.description:
                try:
                    skills = [
                        s.lower() for s in await self.extractor.extract_skills(posting.description)
                    ]
                    parsed_missing += 1
                except Exception:  # noqa: BLE001
                    skills = []
            for s in skills:
                if s:
                    counter[s] += 1

        profile_set = {s.lower() for s in profile.skills}
        gaps = [
            SkillGap(skill=skill, demand_count=count, in_profile=skill in profile_set)
            for skill, count in counter.most_common()
            if skill not in profile_set
        ]
        top_demanded = [SkillDemand(skill=s, count=c) for s, c in counter.most_common(10)]
        if not gaps:
            recommendations = ["No skill gaps detected against saved postings."]
        else:
            recommendations = await self._recommend_async(profile, gaps)
        return SkillGapReport(
            total_postings=len(postings),
            profile_skills=list(profile.skills),
            top_demanded=top_demanded,
            gaps=gaps,
            recommendations=recommendations,
            sourced_from="saved postings"
            + (f" (incl. {parsed_missing} parsed on demand)" if parsed_missing else ""),
        )

    def _recommend(self, profile: UserProfile, gaps: list[SkillGap]) -> list[str]:
        if not gaps:
            return ["No skill gaps detected against saved postings."]
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            return _rule_based_recommendations(gaps)
        return asyncio.run(self._recommend_async(profile, gaps))

    async def _recommend_async(self, profile: UserProfile, gaps: list[SkillGap]) -> list[str]:
        prompt = (
            "Recommend a focused learning path for a candidate whose profile "
            "lacks these in-demand skills (list is demand-ordered). Return strict JSON "
            'list of strings, max 6 items: ["...", ...]\n'
            f"Candidate skills: {', '.join(profile.skills)}\n"
            f"Missing in-demand skills: {', '.join(g.skill for g in gaps[:12])}"
        )
        text = await self.router.generate_text(prompt, task="learning_path")
        if text.startswith(DEGRADATION_TEXT):
            return _rule_based_recommendations(gaps)
        try:
            items = json.loads(text)
            if isinstance(items, list):
                return [str(i) for i in items[:6]]
        except (json.JSONDecodeError, TypeError):
            pass
        return _rule_based_recommendations(gaps)
