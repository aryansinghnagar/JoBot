"""Skill-gap analysis: demand from saved job postings vs candidate profile."""

import asyncio
import json
from collections import Counter
from typing import List, Optional

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
    profile_skills: List[str]
    top_demanded: List[SkillDemand]
    gaps: List[SkillGap]
    recommendations: List[str]
    sourced_from: str


def _rule_based_recommendations(gaps: List[SkillGap], cap: int = 6) -> List[str]:
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
        db: Optional[DatabaseManager] = None,
        extractor: Optional[SkillExtractor] = None,
        router: Optional[ModelRouter] = None,
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

    def _recommend(self, profile: UserProfile, gaps: List[SkillGap]) -> List[str]:
        if not gaps:
            return ["No skill gaps detected against saved postings."]
        return asyncio.run(self._recommend_async(profile, gaps))

    async def _recommend_async(self, profile: UserProfile, gaps: List[SkillGap]) -> List[str]:
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
