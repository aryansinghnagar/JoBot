"""Phase 4 WS1: Application Tracking System — analytics + rendering."""

from datetime import datetime, timezone, timedelta

import pytest
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    TrustLevel,
)
from jobot.storage.db import DatabaseManager
from jobot.tracker.analytics import TrackerAnalytics
from jobot.tracker.render import TrackerRenderer

from typer.testing import CliRunner
from jobot.cli.main import app


@pytest.fixture
def seeded_db(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "test.db")
    base = datetime.now(timezone.utc)
    for job_id, site, title, company in [
        ("J1", "mock_ats", "Senior Backend Engineer", "Mock Corp"),
        ("J2", "greenhouse", "Data Engineer", "GH Co"),
    ]:
        db.save_job_posting(
            JobPosting(
                job_id=job_id,
                site=site,
                url=f"http://x/{job_id}",
                title=title,
                company=company,
                location="Somewhere",
                description="d",
                parsed_skills=["Python"],
            )
        )
    statuses = [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.VERIFIED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.PENDING_APPROVAL,
    ]
    for i, st in enumerate(statuses, start=1):
        responded = (
            (base - timedelta(days=1)).isoformat()
            if st != ApplicationStatus.PENDING_APPROVAL
            else None
        )
        db.save_application(
            Application(
                application_id=f"A{i}",
                job_id="J1" if i <= 3 else "J2",
                site="mock_ats" if i <= 3 else "greenhouse",
                idempotency_key=f"k{i}",
                status=st,
                trust_level=TrustLevel.SUPERVISED,
                created_at=(base - timedelta(days=2)).isoformat(),
                updated_at=base.isoformat(),
                responded_at=responded,
                outcome=st.value if st != ApplicationStatus.PENDING_APPROVAL else None,
            )
        )
    return db


def test_funnel_counts(seeded_db):
    analytics = TrackerAnalytics(seeded_db)
    f = analytics.funnel()
    assert f["total"] == 4
    assert f["pending_approval"] == 1
    assert f["submitted"] == 1
    assert f["verified"] == 1
    assert f["rejected"] == 1
    assert f["failed"] == 0


def test_by_board(seeded_db):
    analytics = TrackerAnalytics(seeded_db)
    boards = analytics.by_board()
    mock = next(b for b in boards if b["site"] == "mock_ats")
    assert mock["total"] == 3
    assert mock["verified"] == 1
    assert mock["rejected"] == 1
    gh = next(b for b in boards if b["site"] == "greenhouse")
    assert gh["total"] == 1


def test_response_rate(seeded_db):
    analytics = TrackerAnalytics(seeded_db)
    # verified=1, rejected=1 -> 0.5
    assert analytics.response_rate() == 0.5


def test_rejection_latency(seeded_db):
    analytics = TrackerAnalytics(seeded_db)
    lat = analytics.rejection_latency_days()
    assert lat["count"] == 3
    assert lat["avg_days"] >= 0.0
    assert lat["median_days"] >= 0.0


def test_html_render(seeded_db, tmp_path):
    analytics = TrackerAnalytics(seeded_db)
    renderer = TrackerRenderer(analytics)
    out = tmp_path / "dashboard.html"
    path = renderer.render_html_file(out, limit=100)
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "JoBot Application Dashboard" in html
    assert "Senior Backend Engineer" in html
    assert "Mock Corp" in html


def test_terminal_status_stamps_responded_at(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "test.db")
    db.save_job_posting(
        JobPosting(
            job_id="J1",
            site="mock_ats",
            url="http://x/1",
            title="Senior Backend Engineer",
            company="Mock Corp",
            description="d",
            parsed_skills=["Python"],
        )
    )
    db.save_application(
        Application(
            application_id="A_NEW",
            job_id="J1",
            site="mock_ats",
            idempotency_key="k_new",
            status=ApplicationStatus.VERIFIED,
            trust_level=TrustLevel.SUPERVISED,
            updated_at=datetime.now(timezone.utc),
        )
    )
    loaded = db.get_application("A_NEW")
    assert loaded is not None
    assert loaded.responded_at is not None
    assert loaded.outcome == "verified"


def test_cli_tracker_list():
    runner = CliRunner()
    result = runner.invoke(app, ["tracker", "list"])
    assert result.exit_code == 0
    # Structure asserts (CLI reads the default DB, not the seeded fixture)
    assert "Applications" in result.stdout
    assert "Funnel:" in result.stdout
    assert "Response rate:" in result.stdout
