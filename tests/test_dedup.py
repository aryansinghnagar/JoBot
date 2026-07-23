from pathlib import Path
import tempfile
import pytest

from jobot.models.domain import Application, ApplicationStatus, JobPosting
from jobot.storage.db import DatabaseManager, DuplicateApplicationError


def test_dedup_rejects_duplicate_idempotency_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_dedup.db")

        job = JobPosting(
            job_id="job_dedup",
            site="naukri",
            url="http://example.com/job/1",
            title="Software Engineer",
            company="Acme",
        )
        db.save_job_posting(job)

        app1 = Application(
            application_id="app_1",
            job_id="job_dedup",
            site="naukri",
            profile_id="p1",
            status=ApplicationStatus.INTENT,
            idempotency_key="unique_key_123",
        )
        db.save_application(app1)
        assert db.application_exists("unique_key_123") is True

        app2 = Application(
            application_id="app_2",
            job_id="job_dedup",
            site="naukri",
            profile_id="p1",
            status=ApplicationStatus.INTENT,
            idempotency_key="unique_key_123",
        )
        with pytest.raises(DuplicateApplicationError):
            db.save_application(app2)
