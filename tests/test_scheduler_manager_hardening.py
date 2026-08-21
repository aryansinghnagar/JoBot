"""Tests for SchedulerManager hardening, cron validation, and ID monotonicity (JOB-AUD-003)."""

import pytest

from jobot.scheduler import SchedulerManager, validate_cron


def test_validate_cron_valid():
    assert validate_cron("0 9 * * *") is True
    assert validate_cron("*/15 * * * *") is True
    assert validate_cron("0 0 1 1 *") is True
    assert validate_cron("0 9 * * 1-5") is True
    assert validate_cron("@daily") is True
    assert validate_cron("@hourly") is True


def test_validate_cron_invalid():
    assert validate_cron("invalid cron") is False
    assert validate_cron("0 9 *") is False  # 3 parts only
    assert validate_cron("0 9 * * * * 2026") is False  # 7 parts


def test_scheduler_manager_add_and_remove_monotonic_id(tmp_path):
    sched_file = tmp_path / "schedules.json"
    mgr = SchedulerManager(schedule_file=sched_file)

    s1 = mgr.add_schedule("0 9 * * *", "jobot run --goal 10")
    s2 = mgr.add_schedule("0 18 * * *", "jobot digest")
    s3 = mgr.add_schedule("*/30 * * * *", "jobot discover")

    assert s1["schedule_id"] == "sch_001"
    assert s2["schedule_id"] == "sch_002"
    assert s3["schedule_id"] == "sch_003"

    # Delete s2 (sch_002)
    assert mgr.remove_schedule("sch_002") is True
    assert len(mgr.list_schedules()) == 2

    # Add s4: should be sch_004 (NOT collides with sch_003)
    s4 = mgr.add_schedule("@daily", "jobot doctor")
    assert s4["schedule_id"] == "sch_004"


def test_scheduler_manager_rejects_invalid_cron(tmp_path):
    mgr = SchedulerManager(schedule_file=tmp_path / "schedules.json")
    with pytest.raises(ValueError, match="Invalid cron expression"):
        mgr.add_schedule("every monday at 9am", "jobot run")
