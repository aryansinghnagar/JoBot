"""Phase 4 WS2: Weekly digest + shared email sender."""

from datetime import datetime, timezone, timedelta

import pytest
from jobot.digest.generator import DigestGenerator
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    TrustLevel,
)
from jobot.notify.email import EmailSender
from jobot.storage.db import DatabaseManager

from typer.testing import CliRunner
from jobot.cli.main import app


@pytest.fixture
def seeded_db(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "test.db")
    db.save_job_posting(
        JobPosting(
            job_id="J1",
            site="mock_ats",
            url="http://x/1",
            title="Senior Backend Engineer",
            company="Mock Corp",
            location="B",
            description="d",
            parsed_skills=["Python"],
        )
    )
    now = datetime.now(timezone.utc)
    for i, st in enumerate(
        [ApplicationStatus.SUBMITTED, ApplicationStatus.VERIFIED, ApplicationStatus.REJECTED],
        start=1,
    ):
        db.save_application(
            Application(
                application_id=f"A{i}",
                job_id="J1",
                site="mock_ats",
                idempotency_key=f"k{i}",
                status=st,
                trust_level=TrustLevel.SUPERVISED,
                created_at=(now - timedelta(days=i)).isoformat(),
                updated_at=now.isoformat(),
                responded_at=(now - timedelta(days=i - 1)).isoformat(),
                outcome=st.value,
            )
        )
    return db


def test_digest_generates_content(seeded_db):
    gen = DigestGenerator(seeded_db, period_days=7)
    digest = gen.generate()
    assert "JoBot Weekly Digest" in digest.html
    assert "Senior Backend Engineer" in digest.html
    assert "Mock Corp" in digest.html
    assert "Response rate" in digest.text
    assert digest.subject.startswith("JoBot weekly digest")


def test_digest_render_file(seeded_db, tmp_path):
    gen = DigestGenerator(seeded_db, period_days=7)
    out = tmp_path / "digest.html"
    path = gen.render_file(out)
    assert path.exists()
    assert "JoBot Weekly Digest" in path.read_text(encoding="utf-8")


def test_email_sender_not_configured():
    # No SMTP config on a clean test environment -> dry refusal, no network.
    sender = EmailSender()
    assert sender.is_configured() is False
    ok, msg = sender.send("t", "<p>hi</p>", body_text="hi")
    assert ok is False
    assert "not configured" in msg.lower()


def test_email_sender_sends_with_fake_factory():
    class FakeSMTP:
        def __init__(self, host, port):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, context=None):
            self.starttls_called = True

        def login(self, user, password):
            self.login_user = user
            self.login_password = password

        def sendmail(self, from_addr, to_addrs, body):
            self.sent = (from_addr, to_addrs, body)
            return {}

        def quit(self):
            pass

    called = {}

    def factory(host, port):
        called["host"] = host
        called["port"] = port
        return FakeSMTP(host, port)

    # Patch config layer to return SMTP values deterministically.
    class FakeConfig:
        def get(self, key, default=None):
            return {
                "smtp.host": "smtp.example.com",
                "smtp.port": "587",
                "smtp.user": "bot",
                "smtp.password": "secret",
                "smtp.from": "bot@example.com",
                "smtp.recipient": "owner@example.com",
            }.get(key, default)

    sender = EmailSender(config=FakeConfig(), smtp_factory=factory)
    assert sender.is_configured() is True
    ok, msg = sender.send("Hello", "<p>hi</p>", body_text="hi")
    assert ok is True
    assert called["host"] == "smtp.example.com"
    assert called["port"] == 587


def test_cli_digest_dry_run(seeded_db):
    runner = CliRunner()
    result = runner.invoke(app, ["digest", "--dry-run"])
    assert result.exit_code == 0
    assert "JoBot weekly digest" in result.stdout
    assert "dry run" in result.stdout.lower()
