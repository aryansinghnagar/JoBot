import tempfile
from pathlib import Path
import pytest
from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager, DuplicateApplicationError
from jobot.storage.vault import CredentialVault


def test_sqlite_db_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(db_path)

        # Save & load JobPosting
        job = JobPosting(
            job_id="job_123",
            site="naukri",
            url="https://naukri.com/job/123",
            title="Senior Backend Engineer",
            company="Acme Corp",
            parsed_skills=["Python", "FastAPI"],
        )
        db.save_job_posting(job)
        loaded_job = db.get_job_posting("job_123")
        assert loaded_job is not None
        assert loaded_job.title == "Senior Backend Engineer"

        # Save & load Application
        app = Application(
            application_id="app_123",
            job_id="job_123",
            site="naukri",
            idempotency_key="idempotency_key_123",
            status=ApplicationStatus.VERIFIED,
            form_values={"name": "Rahul"},
        )
        db.save_application(app)
        loaded_app = db.get_application("app_123")
        assert loaded_app is not None
        assert loaded_app.status == ApplicationStatus.VERIFIED

        # Retrieve by idempotency key
        app_by_key = db.get_application_by_idempotency_key("idempotency_key_123")
        assert app_by_key is not None
        assert app_by_key.application_id == "app_123"


def test_duplicate_application_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "dup_test.db"
        db = DatabaseManager(db_path)

        job = JobPosting(
            job_id="job_001",
            site="naukri",
            url="https://naukri.com/job/001",
            title="Backend Engineer",
            company="Acme Corp",
        )
        db.save_job_posting(job)

        app1 = Application(
            application_id="app_001",
            job_id="job_001",
            site="naukri",
            idempotency_key="unique_key_abc",
            status=ApplicationStatus.SUBMITTED,
        )
        db.save_application(app1)

        # Attempting to save a DIFFERENT application with the SAME idempotency key must raise DuplicateApplicationError
        app2 = Application(
            application_id="app_002",
            job_id="job_001",
            site="naukri",
            idempotency_key="unique_key_abc",
            status=ApplicationStatus.SUBMITTED,
        )
        with pytest.raises(DuplicateApplicationError):
            db.save_application(app2)


def test_credential_vault_encryption():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_dir = Path(tmpdir) / "vault"
        vault = CredentialVault(vault_dir)

        profile = UserProfile(
            profile_id="encrypted_test",
            personal_info=PersonalInfo(first_name="Alice", email="alice@example.com"),
        )

        enc_path = vault.save_encrypted_profile(profile, Path(tmpdir) / "profile.enc")
        assert enc_path.exists()

        loaded_profile = vault.load_encrypted_profile(enc_path)
        assert loaded_profile.personal_info.first_name == "Alice"
        assert loaded_profile.personal_info.email == "alice@example.com"
