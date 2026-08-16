"""Phase 4 WS5: Outreach — LinkedIn URL generation + cold-DM drafts + SMTP send."""

from jobot.outreach.dm import Contact, DMGenerator, OutreachGate, OutreachPreset
from jobot.outreach.links import LinkedInPeopleSearchURLBuilder

__all__ = [
    "Contact",
    "DMGenerator",
    "OutreachGate",
    "OutreachPreset",
    "LinkedInPeopleSearchURLBuilder",
]
