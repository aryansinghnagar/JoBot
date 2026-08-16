"""Cold-DM drafting (profile-grounded) + daily DM cap + SMTP delivery."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml
from pydantic import BaseModel

from jobot.config.profile import load_profile_config
from jobot.llm.router import DEGRADATION_TEXT, ModelRouter
from jobot.models.domain import UserProfile
from jobot.notify.email import EmailSender

PRESETS_PATH = Path(__file__).parent / "presets.yaml"

_PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


class OutreachPreset(BaseModel):
    name: str
    tone: str
    opening: str
    body: str
    closing: str
    call_to_action: str
    min_length: int = 60
    max_length: int = 200


class Contact(BaseModel):
    first_name: str
    company: str
    role: str = ""
    location: Optional[str] = None
    title: Optional[str] = None


class DMResult(BaseModel):
    preset: str
    text: str
    grounded: bool
    source: str  # "llm" | "template-fallback"


class OutreachGate:
    """Enforces the daily DM cap from OutreachConfig."""

    def __init__(self, state_path: Optional[Path] = None, daily_cap: int = 5) -> None:
        self.state_path = Path(
            state_path or (Path.home() / ".jobot" / "data" / "outreach_state.json")
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.daily_cap = daily_cap

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self) -> Dict[str, int]:
        if not self.state_path.exists():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def sent_today(self) -> int:
        return self._load().get(self._today(), 0)

    def remaining(self) -> int:
        return max(0, self.daily_cap - self.sent_today())

    def record_send(self) -> None:
        data = self._load()
        data[self._today()] = data.get(self._today(), 0) + 1
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def can_send(self) -> bool:
        return self.sent_today() < self.daily_cap


class DMGenerator:
    """Drafts profile-grounded cold DMs from presets; sends via EmailSender."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        presets_path: Optional[Path] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.presets_path = Path(presets_path or PRESETS_PATH)
        self._presets: Dict[str, OutreachPreset] = {}

    def presets(self) -> Dict[str, OutreachPreset]:
        if not self._presets:
            raw = yaml.safe_load(self.presets_path.read_text(encoding="utf-8")) or {}
            self._presets = {k: OutreachPreset(**v) for k, v in raw.get("presets", {}).items()}
        return self._presets

    def get_preset(self, key: str) -> OutreachPreset:
        presets = self.presets()
        if key not in presets:
            raise ValueError(f"unknown outreach preset '{key}'; one of {sorted(presets)}")
        return presets[key]

    def _fill_template(self, preset: OutreachPreset, contact: Contact, profile: UserProfile) -> str:
        mapping = {
            "first_name": contact.first_name,
            "company": contact.company,
            "role": contact.role or "open",
            "company_focus": "innovative products",
            "candidate_name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}",
            "candidate_role": "backend engineer",
            "candidate_skills": ", ".join(profile.skills[:5]),
            "candidate_experience_years": str(max(1, len(profile.experiences) or 1)),
        }
        parts = [preset.opening, preset.body, preset.closing, preset.call_to_action]
        text = "\n\n".join(parts).format(**mapping)
        return re.sub(r"\s+", " ", text).strip()

    def _grounded(self, text: str, profile: UserProfile) -> bool:
        if "@" in text and profile.personal_info.email not in text:
            return False
        phone = profile.personal_info.phone
        if phone and phone in text:
            pass  # phone from profile is allowed
        return _PLACEHOLDER_RE.search(text) is None

    async def draft(
        self,
        preset_key: str,
        contact: Contact,
        profile: UserProfile,
    ) -> DMResult:
        preset = self.get_preset(preset_key)
        prompt = (
            "Write a concise cold outreach message (single channel, no subject line) "
            f"for a {preset.tone} tone. Only use these candidate facts — never invent: "
            f"name {profile.personal_info.first_name} {profile.personal_info.last_name}, "
            f"skills {', '.join(profile.skills)}, current role/company from experience: "
            f"{'; '.join(e.title + ' @ ' + e.company for e in profile.experiences[:2])}. "
            f"Recipient first name: {contact.first_name}, company: {contact.company}, "
            f"target role: {contact.role or 'open'}. Keep it under {preset.max_length} words, "
            f"personal, and end with a single call-to-action question."
        )
        text = await self.router.generate_text(prompt, task="outreach_dm")
        if text.startswith(DEGRADATION_TEXT):
            return DMResult(
                preset=preset_key,
                text=self._fill_template(preset, contact, profile),
                grounded=True,
                source="template-fallback",
            )
        text = text.strip()
        grounded = self._grounded(text, profile)
        return DMResult(
            preset=preset_key,
            text=text,
            grounded=grounded,
            source="llm",
        )

    def send(
        self,
        dm: DMResult,
        contact: Contact,
        gate: Optional[OutreachGate] = None,
        email: Optional[EmailSender] = None,
    ) -> Tuple[bool, str]:
        gate = gate or OutreachGate(daily_cap=load_profile_config().outreach.daily_dm_cap)
        if not gate.can_send():
            return False, f"daily DM cap reached ({gate.sent_today()}/{gate.daily_cap})"
        email = email or EmailSender()
        if not email.is_configured():
            return False, "SMTP not configured"
        subject = f"Outreach to {contact.first_name} at {contact.company}"
        ok, msg = email.send(subject, dm.text.replace("\n", "<br>"), body_text=dm.text)
        if ok:
            gate.record_send()
        return ok, msg
