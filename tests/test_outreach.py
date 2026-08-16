"""Phase 4 WS5: Outreach — presets, URL builder, DM gen, daily cap, CLI."""

import pytest
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import (
    CompensationDetails,
    Education,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)
from jobot.outreach.dm import Contact, DMGenerator, OutreachGate
from jobot.outreach.links import LinkedInPeopleSearchURLBuilder
from typer.testing import CliRunner

from jobot.cli.main import app


def make_profile() -> UserProfile:
    return UserProfile(
        profile_id="p_out",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Sharma",
            email="aryan@example.com",
            phone="+911234567890",
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI", "Django"],
        experiences=[
            WorkExperience(
                title="Engineer",
                company="Mock Corp",
                start_date="2021",
                end_date="Present",
                description="Built REST APIs in Python.",
            )
        ],
        education=[Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)],
    )


CONTACT = Contact(first_name="Priya", company="Acme Labs", role="Staff Engineer")


class FakeRouter:
    def __init__(self, reply=None, degrade=False):
        self.reply = reply
        self.degrade = degrade

    async def generate_text(self, prompt, **kwargs):
        if self.degrade:
            return DEGRADATION_TEXT
        return self.reply or (
            "Hi Priya, I'm Aryan Sharma — I build Python and FastAPI systems. "
            "I'd love to discuss Staff Engineer opportunities at Acme Labs. "
            "Would you be open to a 15-minute call this week?"
        )


def test_presets_load():
    gen = DMGenerator()
    presets = gen.presets()
    assert set(presets) == {"faang_senior", "startup_founding", "quant_finance"}
    for p in presets.values():
        assert p.opening and p.body and p.closing and p.call_to_action


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="unknown outreach preset"):
        DMGenerator().get_preset("bogus")


def test_url_builder_deterministic():
    builder = LinkedInPeopleSearchURLBuilder()
    url = builder.build_for_contact("Priya Sharma", company="Acme Labs", role="Staff Engineer")
    assert url.startswith("https://www.linkedin.com/search/results/people/")
    assert "keywords=Priya+Sharma" in url
    assert "currentCompany=Acme+Labs" in url
    assert url == builder.build_for_contact("Priya Sharma", company="Acme Labs", role="Staff Engineer")


def test_url_builder_escapes():
    builder = LinkedInPeopleSearchURLBuilder()
    url = builder.build("A&B C")
    assert "keywords=A%26B+C" in url


@pytest.mark.asyncio
async def test_dm_generation_llm_path():
    gen = DMGenerator(router=FakeRouter())
    dm = await gen.draft("faang_senior", CONTACT, make_profile())
    assert dm.source == "llm"
    assert dm.grounded is True
    assert "Priya" in dm.text


@pytest.mark.asyncio
async def test_dm_generation_template_fallback():
    gen = DMGenerator(router=FakeRouter(degrade=True))
    dm = await gen.draft("faang_senior", CONTACT, make_profile())
    assert dm.source == "template-fallback"
    assert dm.grounded is True
    assert "{first_name}" not in dm.text
    assert "Priya" in dm.text
    assert "Aryan Sharma" in dm.text


@pytest.mark.asyncio
async def test_dm_grounding_rejects_invented_facts():
    gen = DMGenerator(
        router=FakeRouter(reply="Hi Priya, I previously worked at SpaceX (contact: me@nowhere.example). Call me!")
    )
    dm = await gen.draft("faang_senior", CONTACT, make_profile())
    assert dm.grounded is False


def test_outreach_gate_cap(tmp_path):
    gate = OutreachGate(state_path=tmp_path / "state.json", daily_cap=2)
    assert gate.can_send() is True
    gate.record_send()
    gate.record_send()
    assert gate.can_send() is False
    assert gate.remaining() == 0


def test_outreach_gate_resets_daily(tmp_path):
    gate = OutreachGate(state_path=tmp_path / "state.json", daily_cap=2)
    gate.record_send()
    gate.record_send()
    state = gate._load()
    assert state and gate.sent_today() == 2


def test_send_refuses_over_cap(tmp_path):
    gate = OutreachGate(state_path=tmp_path / "state.json", daily_cap=1)
    gate.record_send()

    class FakeEmail:
        def is_configured(self):
            return True

        def send(self, subject, body_html, body_text=None):
            return True, "sent"

    gen = DMGenerator(router=FakeRouter(degrade=True))
    from jobot.outreach.dm import DMResult

    ok, msg = gen.send(
        DMResult(preset="faang_senior", text="Hi", grounded=True, source="template-fallback"),
        CONTACT,
        gate=gate,
        email=FakeEmail(),
    )
    assert ok is False
    assert "cap" in msg


def test_cli_outreach_presets(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["outreach", "presets"])
    assert result.exit_code == 0
    assert "faang_senior" in result.stdout


def test_cli_outreach_draft_requires_profile(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["outreach", "draft", "--preset", "faang_senior", "--name", "Priya", "--company", "Acme"],
    )
    assert result.exit_code == 1
    assert "profile" in result.stdout.lower()


def test_cli_outreach_send_requires_profile(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["outreach", "send", "--preset", "faang_senior", "--name", "Priya", "--company", "Acme"],
    )
    assert result.exit_code == 1
    assert "profile" in result.stdout.lower()