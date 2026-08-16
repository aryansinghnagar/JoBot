import pytest
from jobot.documents.tailor import DocumentTailor
from jobot.models.domain import JobPosting, PersonalInfo, UserProfile
from jobot.security.audit import SecurityAuditor
from jobot.stealth.behavior import BehavioralMimicry
from jobot.stealth.proxy import ProxyConfig, ProxyManager
from jobot.updater import ReleaseManager


def test_behavioral_mimicry_bezier_and_typing():
    bezier_points = BehavioralMimicry.generate_bezier_curve((0, 0), (500, 500))
    assert len(bezier_points) > 20
    assert bezier_points[0] == (0, 0)
    assert bezier_points[-1] == (500, 500)

    typing_delays = BehavioralMimicry.get_keystroke_delays("Hello World!")
    assert len(typing_delays) == len("Hello World!")
    assert all(d > 0.05 for d in typing_delays)


def test_proxy_manager_rotation():
    pm = ProxyManager()
    p1 = ProxyConfig(proxy_id="p1", server="1.1.1.1", port=8080, country="IN")
    p2 = ProxyConfig(proxy_id="p2", server="2.2.2.2", port=8080, country="IN")
    pm.add_proxy(p1)
    pm.add_proxy(p2)

    selected = pm.get_proxy_for_site("naukri", country="IN")
    assert selected is not None
    assert selected.country == "IN"

    pm.mark_unhealthy("p1")
    pm.mark_unhealthy("p2")
    assert pm.get_proxy_for_site("naukri", country="IN") is None


@pytest.mark.asyncio
async def test_document_tailoring():
    tailor = DocumentTailor()
    job = JobPosting(
        job_id="j_tailor",
        site="naukri",
        url="https://naukri.com/job/101",
        title="Senior Python Engineer",
        company="Acme Corp",
        parsed_skills=["Python", "FastAPI"],
    )
    profile = UserProfile(
        profile_id="p_tailor",
        personal_info=PersonalInfo(first_name="Rahul", last_name="Sharma"),
        skills=["Python", "FastAPI", "SQLite"],
    )

    result = await tailor.generate_tailored_materials(job, profile)
    assert result.is_truthful is True
    assert "Python" in result.highlighted_skills


def test_security_auditor_and_release_manager():
    auditor = SecurityAuditor()
    profile = UserProfile()
    report = auditor.audit_profile_security(profile)
    assert report.is_secure is True

    rel_mgr = ReleaseManager()
    status = rel_mgr.check_for_updates()
    assert status.current_version == "1.0.0"
    assert rel_mgr.rollback() is True
