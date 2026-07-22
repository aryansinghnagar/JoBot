import pytest
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.models.domain import JobPosting, PersonalInfo, UserProfile


@pytest.mark.asyncio
async def test_job_discovery_and_matching():
    discovery = JobDiscoveryEngine(active_portals=["naukri", "linkedin"])

    profile = UserProfile(
        profile_id="p_disc",
        personal_info=PersonalInfo(first_name="Rahul", last_name="Sharma"),
        skills=["Python", "FastAPI", "SQLite"],
    )

    # Evaluate matching
    posting = JobPosting(
        job_id="j_disc",
        site="naukri",
        url="https://naukri.com/job/101",
        title="Python Engineer",
        company="Acme Corp",
        parsed_skills=["Python", "FastAPI"],
    )

    match_res = discovery.evaluate_match(posting, profile)
    assert match_res.match_score == 1.0
    assert match_res.recommendation == "HIGH_FIT"
    assert "Python" in match_res.matching_skills

    # Discover jobs across portals
    discovered = await discovery.discover_matching_jobs(profile, target_title="Python Developer")
    assert len(discovered) > 0
    assert all(d.recommendation in ["HIGH_FIT", "MEDIUM_FIT"] for d in discovered)
