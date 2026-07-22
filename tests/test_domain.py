import pytest
from jobot.models.domain import ApplicationStatus, CompensationDetails, PersonalInfo, UserProfile, WorkExperience


def test_user_profile_creation():
    profile = UserProfile(
        profile_id="test_profile",
        personal_info=PersonalInfo(
            first_name="Rahul",
            last_name="Sharma",
            email="rahul@example.com",
            phone="+919876543210",
        ),
        compensation=CompensationDetails(
            current_ctc_inr=1200000,
            expected_ctc_inr=1800000,
            notice_period_days=30,
        ),
        skills=["Python", "FastAPI"],
    )

    assert profile.profile_id == "test_profile"
    assert profile.personal_info.first_name == "Rahul"
    assert profile.compensation.notice_period_days == 30
    assert "Python" in profile.skills


def test_application_status_enum_additions():
    assert ApplicationStatus.REJECTED.value == "rejected"
    assert ApplicationStatus.BLOCKED.value == "blocked"
    assert ApplicationStatus.CIRCUIT_OPEN.value == "circuit_open"
    assert ApplicationStatus.DUPLICATE_SKIPPED.value == "duplicate_skipped"
    assert ApplicationStatus.CANCELLED.value == "cancelled"
