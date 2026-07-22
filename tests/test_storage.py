import tempfile
from pathlib import Path
import pytest
from jobaut.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobaut.storage.db import DatabaseManager
from jobaut.storage.vault import CredentialVault


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
