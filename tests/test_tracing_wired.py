from pathlib import Path
import tempfile
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import PersonalInfo, UserProfile
from jobot.obs.tracing import TraceLogger
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_trace_logger_persists_spans():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DatabaseManager(tmp_path / "test_tr.db")
        tl = TraceLogger(trace_dir=tmp_path / "traces", run_id="test_run_123")
        adapter = MockATSAdapter(base_url="http://127.0.0.1:5800")
        pipeline = ApplicationSubmissionPipeline(adapter, db, trace_logger=tl)

        profile = UserProfile(
            profile_id="p_tr",
            personal_info=PersonalInfo(first_name="Aryan", email="tr@example.com"),
        )

        job_url = "http://127.0.0.1:5800/jobs/1"
        await pipeline.execute(job_url, profile, auto_approve=True)

        spans = tl.get_trace_spans("test_run_123")
        assert len(spans) >= 3
        span_names = [s["name"] for s in spans]
        assert "phase_2_parse" in span_names
        assert "phase_6_fill_form" in span_names
