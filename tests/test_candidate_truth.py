"""Tests for Candidate Truth System, Grounding Verifier, Answer Bank, and Form Field Memory (UC-21 & UC-26)."""

from pathlib import Path

import pytest

from jobot.ai.candidate_truth import (
    CandidateGroundingVerifier,
    CandidateTruthStore,
)
from jobot.ai.qa_engine import QAEngine
from jobot.models.domain import (
    AnswerBankRecord,
    CompensationDetails,
    Education,
    FormFieldMemoryRecord,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)
from jobot.storage.db import DatabaseManager


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    return DatabaseManager(tmp_path / "test_truth.db")


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        profile_id="aryan-test",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="aryan@example.com",
            phone="9876543210",
            location_city="Mumbai",
            location_state="Maharashtra",
        ),
        experiences=[
            WorkExperience(
                company="TechCorp",
                title="Senior Software Engineer",
                start_date="2022-01",
                end_date="2024-05",
                description="Built distributed real-time backend systems in Python and Go",
                technologies=["Python", "Go", "PostgreSQL", "Kafka"],
            )
        ],
        education=[
            Education(
                institution="IIT Bombay",
                degree="B.Tech",
                field_of_study="Electrical Engineering",
                start_year=2018,
                end_year=2022,
            )
        ],
        skills=["Python", "Go", "PostgreSQL", "Docker", "Kubernetes", "Machine Learning"],
        compensation=CompensationDetails(
            current_ctc_inr=1500000.0,
            expected_ctc_inr=2200000.0,
            notice_period_days=30,
        ),
    )


def test_candidate_truth_store_seed_and_query(
    test_db: DatabaseManager, sample_profile: UserProfile
):
    store = CandidateTruthStore(test_db)
    facts = store.seed_from_profile(sample_profile)
    assert len(facts) > 10

    loaded_facts = store.get_facts(profile_id="aryan-test")
    assert len(loaded_facts) == len(facts)

    skills = store.get_facts(profile_id="aryan-test", fact_type="skill")
    skill_values = [f.fact_value for f in skills]
    assert "Python" in skill_values
    assert "Docker" in skill_values

    edu = store.get_facts(profile_id="aryan-test", fact_type="education")
    assert any("IIT Bombay" in f.fact_value for f in edu)


def test_grounding_verifier_valid_claims(test_db: DatabaseManager, sample_profile: UserProfile):
    store = CandidateTruthStore(test_db)
    store.seed_from_profile(sample_profile)
    verifier = CandidateGroundingVerifier(store)

    valid_text = (
        "I graduated with a B.Tech in Electrical Engineering from IIT Bombay. "
        "At TechCorp, I worked as a Senior Software Engineer building Python and Go systems."
    )
    result = verifier.verify_text(valid_text, profile_id="aryan-test")
    assert result.passed is True
    assert result.score >= 0.8
    assert len(result.unsupported_claims) == 0


def test_grounding_verifier_detects_hallucinations(
    test_db: DatabaseManager, sample_profile: UserProfile
):
    store = CandidateTruthStore(test_db)
    store.seed_from_profile(sample_profile)
    verifier = CandidateGroundingVerifier(store)

    # Fabricated university and fake email
    hallucinated_text = (
        "I completed my PhD in Computer Science at Stanford University. "
        "Contact me at fake_hacker@mit.edu."
    )
    result = verifier.verify_text(hallucinated_text, profile_id="aryan-test")
    assert result.passed is False
    assert len(result.unsupported_claims) > 0
    assert any(
        "Stanford" in claim or "fake_hacker" in claim or "PhD" in claim
        for claim in result.unsupported_claims
    )


def test_answer_bank_persistence_and_search(test_db: DatabaseManager):
    entry1 = AnswerBankRecord(
        profile_id="aryan-test",
        question_hash="hash123",
        question_text="What is your greatest technical challenge?",
        answer="Designing an ultra-low latency event streaming engine.",
        source="llm_grounded",
        used_count=1,
    )
    test_db.save_answer_bank_entry(entry1)

    fetched = test_db.get_answer_bank_entry("aryan-test", "hash123")
    assert fetched is not None
    assert fetched.answer == "Designing an ultra-low latency event streaming engine."

    test_db.record_answer_bank_use("aryan-test", "hash123")
    updated = test_db.get_answer_bank_entry("aryan-test", "hash123")
    assert updated is not None
    assert updated.used_count == 2

    search_res = test_db.search_answer_bank("aryan-test", query="technical challenge")
    assert len(search_res) == 1
    assert search_res[0].question_hash == "hash123"


def test_form_field_memory_persistence(test_db: DatabaseManager):
    rec = FormFieldMemoryRecord(
        profile_id="aryan-test",
        adapter_id="greenhouse",
        field_selector="input#first_name",
        field_label="First Name",
        field_type="text",
        value="Aryan",
        confidence=1.0,
    )
    test_db.save_form_field_memory(rec)

    fetched = test_db.get_form_field_memory("aryan-test", "greenhouse", "input#first_name")
    assert fetched is not None
    assert fetched.value == "Aryan"
    assert fetched.field_label == "First Name"


@pytest.mark.asyncio
async def test_qa_engine_uses_answer_bank_and_grounding(
    test_db: DatabaseManager, sample_profile: UserProfile
):
    qa = QAEngine(db=test_db)

    # 1. Direct answer check
    res_email = await qa.answer_question("What is your email address?", sample_profile)
    assert res_email.answer == "aryan@example.com"
    assert res_email.is_grounded is True

    # 2. Seed answer bank and verify hit
    entry = AnswerBankRecord(
        profile_id="aryan-test",
        question_hash="custom_q_hash",
        question_text="Why do you want to join us?",
        answer="I love solving difficult systems scalability problems.",
        source="user",
        used_count=1,
    )
    import hashlib

    q_text = "Why do you want to join us?"
    h = hashlib.sha256(q_text.lower().encode("utf-8")).hexdigest()
    entry.question_hash = h
    test_db.save_answer_bank_entry(entry)

    res_behavioral = await qa.answer_question(q_text, sample_profile)
    assert res_behavioral.answer == "I love solving difficult systems scalability problems."
    assert res_behavioral.is_grounded is True
