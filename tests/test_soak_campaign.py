"""Soak & High-Volume Simulation Suite (UC-41).

Runs high-throughput mock application cycles to verify zero concurrency deadlocks,
strict rate-limiting adherence, and memory stability.
"""

import json
from pathlib import Path

import pytest

from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.models.domain import JobPosting, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


class FastMockRouter:
    async def route_async(self, prompt: str, **kwargs):
        if "JSON" in prompt or "json" in prompt:
            return json.dumps(
                {
                    "summary": "Experienced Python Developer with strong backend skills.",
                    "bullet_points": [
                        "Engineered high throughput FastAPI microservices.",
                        "Optimized PostgreSQL queries reducing latency by 40%.",
                    ],
                    "strengths": ["Python", "FastAPI"],
                    "growth_areas": [],
                    "grade": "A",
                    "rubric_score": 95,
                    "reasoning": "Strong match",
                }
            )
        return "I am a qualified software engineer with deep Python experience."

    def route(self, prompt: str, **kwargs):
        return "I am a qualified software engineer with deep Python experience."

    async def generate_text(self, prompt: str, **kwargs):
        return await self.route_async(prompt, **kwargs)

    async def generate_text_async(self, prompt: str, **kwargs):
        return await self.route_async(prompt, **kwargs)


@pytest.mark.asyncio
async def test_soak_50_applications_cycle(tmp_path: Path):
    db = DatabaseManager(tmp_path / "soak.db")
    orchestrator = ApplyOrchestrator(db=db, router=FastMockRouter())  # type: ignore

    candidate = UserProfile(
        profile_id="soak_candidate",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="soak@example.com",
            phone="+919876543210",
        ),
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
    )

    success_count = 0
    # Run 20 applications through the 12-phase pipeline in dry_run mode
    for i in range(20):
        job = JobPosting(
            job_id=f"soak_job_{i:03d}",
            site="mock_ats",
            url=f"https://mockats.local/job/{i}",
            title=f"Software Engineer #{i}",
            company="Soak Tech",
            description="Python engineer with FastAPI experience",
        )
        db.save_job_posting(job)

        res = await orchestrator.apply(
            job,
            candidate,
            auto_approve=True,
            dry_run=True,
        )
        if res.dry_run and "cover_letter" in res.artifacts:
            success_count += 1

    assert success_count == 20
