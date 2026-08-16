from pathlib import Path
import tempfile
import threading
import time
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.ai.qa_engine import QAEngine, QuestionType
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager
from tests.mock_ats.server import app as flask_app


class MockQuestionAdapter(MockATSAdapter):
    async def extract_form_questions(self, job):
        return [
            "What is your email address?",
            "Describe a challenging technical project you built.",
            "Please enter your Aadhaar / SSN number.",
        ]


@pytest.mark.asyncio
async def test_qa_engine_wired_in_pipeline(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_qa.db")
        qa = QAEngine()
        adapter = MockQuestionAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, qa_engine=qa)

        profile = UserProfile(
            profile_id="qa_prof",
            personal_info=PersonalInfo(
                first_name="Aryan", last_name="Nagar", email="aryan_qa@example.com"
            ),
            skills=["Python", "FastAPI"],
        )

        job_url = f"{live_mock_ats_server}/jobs/1"
        app_res = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app_res.form_values is not None
        assert "What is your email address?" in app_res.form_values
        assert app_res.form_values["What is your email address?"] == "aryan_qa@example.com"
        assert "Please enter your Aadhaar / SSN number." in app_res.form_values
        assert app_res.form_values["Please enter your Aadhaar / SSN number."] == "[SENSITIVE_FIELD_PAUSED]"
