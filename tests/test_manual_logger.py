import pytest
from jobot.obs.manual_test_logger import ManualTestLogger


def test_manual_test_logger_recording(tmp_path):
    logger = ManualTestLogger(log_dir=tmp_path)

    # 1. Log a user-reported bug
    iss1 = logger.log_issue(
        summary="UI button overlap on Naukri apply form",
        issue_type="USER_REPORT",
        site="naukri",
        details="Button overlap observed on 1080p display",
    )
    assert iss1.issue_type == "USER_REPORT"
    assert iss1.site == "naukri"

    # 2. Log an exception
    try:
        raise ValueError("Simulated network timeout during form fill")
    except Exception as exc:
        iss2 = logger.log_issue(
            summary="Network timeout during apply",
            issue_type="ERROR",
            site="linkedin",
            exc=exc,
        )
        assert iss2.stack_trace is not None
        assert "ValueError: Simulated network timeout" in iss2.stack_trace

    # 3. Retrieve logged issues
    issues = logger.list_issues()
    assert len(issues) == 2
    assert logger.markdown_report.exists()
