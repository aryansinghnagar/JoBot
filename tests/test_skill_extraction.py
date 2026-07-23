import pytest
from jobot.ai.skill_extractor import SkillExtractor


@pytest.mark.asyncio
async def test_skill_extractor_rule_based_fallback():
    extractor = SkillExtractor()
    desc = """
    We are looking for a Senior Backend Engineer proficient in Python, FastAPI, and PostgreSQL.
    Experience with Docker, Kubernetes, and System Design is required.
    """
    skills = await extractor.extract_skills(desc)

    assert len(skills) >= 4
    skills_lower = [s.lower() for s in skills]
    assert "python" in skills_lower
    assert "fastapi" in skills_lower
    assert "postgresql" in skills_lower
    assert "docker" in skills_lower


@pytest.mark.asyncio
async def test_skill_extractor_empty_description():
    extractor = SkillExtractor()
    assert await extractor.extract_skills("") == []
    assert await extractor.extract_skills("Short text") == []
