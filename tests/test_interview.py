"""Phase 4 WS3: InterviewPrep — mock sessions, STAR coach, CLI."""

import pytest
from typer.testing import CliRunner

from jobot.cli.main import app
from jobot.interview.banks import QuestionBank
from jobot.interview.coach import MockInterviewer, STARCoach, _rule_based_score
from jobot.interview.sessions import SessionStore
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import (
    CompensationDetails,
    Education,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)


def make_profile() -> UserProfile:
    return UserProfile(
        profile_id="p_int",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Sharma",
            email="aryan@example.com",
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI"],
        experiences=[
            WorkExperience(
                title="Engineer",
                company="Mock Corp",
                start_date="2021",
                end_date="Present",
                description="Built REST APIs in Python with FastAPI.",
            )
        ],
        education=[
            Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)
        ],
    )


class FakeRouter:
    def __init__(self, reply=None, degrade=False):
        self.reply = reply
        self.degrade = degrade
        self.prompts = []

    async def generate_text(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if self.degrade:
            return DEGRADATION_TEXT
        return self.reply or (
            '{"scores": {"situation": 1.0, "task": 0.8, "action": 1.0, "result": 0.9}, '
            '"feedback": "Strong structure; quantify the result.", "star_present": true}'
        )


@pytest.fixture
def bank():
    return QuestionBank()


def test_bank_loads_all_tracks(bank):
    for track in ("behavioral", "system_design", "technical"):
        qs = bank.questions(track)
        assert len(qs) >= 5
        assert all(q.track == track for q in qs)


def test_bank_rejects_unknown_track(bank):
    with pytest.raises(ValueError, match="unknown interview track"):
        bank.questions("bogus")


def test_bank_next_skips_asked(bank):
    qs = bank.questions("behavioral")
    asked = [qs[0].id]
    nxt = bank.next_question("behavioral", asked)
    assert nxt.id not in asked


@pytest.mark.asyncio
async def test_mock_interviewer_session_flow(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    interviewer = MockInterviewer(store=store, coach=STARCoach(router=FakeRouter()))
    session = interviewer.start("behavioral")
    assert session.status == "active"
    assert store.load(session.session_id) is not None

    turn = await interviewer.answer(
        session, "I led a migration of our API to FastAPI.", make_profile()
    )
    assert turn.star_score > 0.5
    assert turn.question_id not in session.asked_ids[: session.asked_ids.index(turn.question_id)]
    saved = store.load(session.session_id)
    assert len(saved.turns) == 1
    assert saved.turns[0].feedback

    interviewer.complete(session)
    assert store.load(session.session_id).status == "completed"
    assert interviewer.average_score(session) == round(turn.star_score, 3)


@pytest.mark.asyncio
async def test_star_coach_degrades_gracefully(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    interviewer = MockInterviewer(
        store=store,
        coach=STARCoach(router=FakeRouter(degrade=True)),
    )
    session = interviewer.start("behavioral")
    turn = await interviewer.answer(
        session, "I built a dashboard that reduced load time by half.", make_profile()
    )
    assert turn.star_score > 0.0
    assert turn.feedback


@pytest.mark.asyncio
async def test_star_coach_grounding_gate_rejects_invented_facts(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    interviewer = MockInterviewer(
        store=store,
        coach=STARCoach(router=FakeRouter()),
    )
    session = interviewer.start("behavioral")
    turn = await interviewer.answer(
        session, "My email is fake@nowhere.example and I was CTO at SpaceX.", make_profile()
    )
    assert turn.star_score == 0.0
    assert "grounding" in turn.feedback.lower()


@pytest.mark.asyncio
async def test_answer_with_no_questions_left_raises(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    interviewer = MockInterviewer(
        store=store,
        coach=STARCoach(router=FakeRouter()),
    )
    session = interviewer.start("behavioral")
    session.asked_ids = [q.id for q in QuestionBank().questions("behavioral")]
    with pytest.raises(ValueError, match="no questions remaining"):
        await interviewer.answer(session, "anything", make_profile())


def test_rule_based_score_detects_components():
    good = _rule_based_score(
        "In my last role I was working on a slow API. My task was to cut latency. "
        "I implemented caching. This reduced p95 latency by 40%."
    )
    assert good.scores["action"] == 1.0
    assert good.scores["result"] == 1.0
    assert good.star_score > 0.5

    poor = _rule_based_score("I am a backend engineer with 3 years of experience.")
    assert all(v == 0.0 for v in poor.scores.values())


def test_cli_interview_flow(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["interview", "start", "behavioral"])
    assert result.exit_code == 0
    assert "int_" in result.stdout
    assert (tmp_path / ".jobot" / "interviews").exists()


def test_cli_interview_unknown_track(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["interview", "start", "bogus"])
    assert result.exit_code == 1
    assert "unknown interview track" in result.stdout.lower()
