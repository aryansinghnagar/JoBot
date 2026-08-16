"""Phase 3 T3.1: document stack — compiler, templates, PDF renderers, ATS scorer."""

import pytest
from jobot.documents import (
    AtsScorer,
    ResumeExporter,
    compile_resume_data,
    escape_latex,
    get_renderer,
    render_tex,
)
from jobot.models.domain import (
    CompensationDetails,
    Education,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)


def realistic_profile() -> UserProfile:
    experiences = [
        WorkExperience(
            title="Senior Engineer",
            company="Acme",
            start_date="2021",
            end_date="Present",
            description=(
                "Built and scaled REST APIs in Python with FastAPI and PostgreSQL; "
                "owned CI/CD pipelines; mentored 3 juniors."
            ),
        ),
        WorkExperience(
            title="Software Developer",
            company="Beta Labs",
            start_date="2019",
            end_date="2021",
            description=(
                "Developed features for a Django web platform; integrated Stripe "
                "payments; wrote unit tests."
            ),
        ),
        WorkExperience(
            title="Junior Developer",
            company="Gamma",
            start_date="2017",
            end_date="2019",
            description="Maintained internal tooling and MySQL reporting dashboards.",
        ),
    ]
    return UserProfile(
        profile_id="p_docs",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Sharma",
            email="aryan@example.com",
            phone="+911234567890",
            location_city="Bangalore",
            location_country="India",
            linkedin_url="https://linkedin.com/in/aryan",
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI", "Django", "PostgreSQL", "SQLite"],
        experiences=experiences,
        education=[Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)],
    )


def test_render_tex_all_templates():
    data = compile_resume_data(realistic_profile(), summary="Backend engineer.")
    for template in ("default", "modern", "classic"):
        tex = render_tex(data, template)
        assert "\\documentclass" in tex
        assert "Aryan" in tex


def test_unknown_template_raises():
    data = compile_resume_data(realistic_profile())
    with pytest.raises(ValueError):
        render_tex(data, "nonexistent")


def test_escape_latex():
    assert escape_latex("100% {match}") == r"100\% \{match\}"
    assert escape_latex("C++ & Go") == r"C++ \& Go"
    assert escape_latex("") == ""


def test_compile_resume_data_merges_only_grounded_bullets():
    profile = realistic_profile()
    data = compile_resume_data(
        profile,
        summary="Summary text",
        experience_bullets={
            "Acme|Senior Engineer": ["Shipped 3 services"],
            "Phantom Co|CEO": ["Invented role"],  # not in profile -> dropped
        },
    )
    sections = {s.heading: s for s in data.sections}
    exp = sections["WORK EXPERIENCE"]
    acme = next(e for e in exp.entries if e.subtitle == "Acme")
    assert acme.bullets == ["Shipped 3 services"]
    assert all(e.subtitle != "Phantom Co" for e in exp.entries)


def test_to_plain_text_contains_sections():
    data = compile_resume_data(realistic_profile(), summary="S")
    text = data.to_plain_text()
    assert "--- SKILLS SUMMARY ---" in text
    assert "--- WORK EXPERIENCE ---" in text
    assert "--- EDUCATION ---" in text
    assert "aryan@example.com" in text


def test_fallback_pdf_render_and_ats_pass(tmp_path):
    exporter = ResumeExporter()
    pdf, score = exporter.export_resume_pdf(
        realistic_profile(),
        summary="Backend engineer with 6+ years building Python services.",
        engine="fallback",
        output_dir=tmp_path,
    )
    assert pdf.exists()
    assert score.score >= 0.85
    assert score.passed is True


def test_get_renderer_fallback_when_no_tex(monkeypatch):
    import jobot.documents.engines as engines

    monkeypatch.setattr(engines, "tex_engine_available", lambda: False)
    renderer = get_renderer()
    assert renderer.name == "reportlab"
    renderer = get_renderer(prefer="latex")
    assert renderer.name == "reportlab"


def test_ats_scorer_rejects_multi_column_text():
    text = "Python    FastAPI    Django    SQLite\n2021      2022      2023      2024\n"
    score = AtsScorer().score_text(text)
    assert score.details["passed_checks"]["single_column"] is False


def test_ats_scorer_requires_email():
    text = "\n".join(
        [
            "SKILLS",
            "Python",
            "WORK EXPERIENCE",
            "- Built APIs",
            "- Shipped services",
            "- Mentored juniors",
            "EDUCATION",
            "B.Tech",
        ]
    )
    score = AtsScorer().score_text(text)
    assert score.details["passed_checks"]["email"] is False
    assert score.score < 0.85