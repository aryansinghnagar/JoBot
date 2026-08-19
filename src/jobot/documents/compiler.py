"""Resume data model + Jinja2 LaTeX template rendering (Phase 3, T3.1).

Single source of truth for resume content: a structured `ResumeData` tree that
is rendered to LaTeX (lualatex/xelatex), plain text, and — via engines.py —
to PDF. Tailored content (T3.2) is merged here, never fabricated: experience
bullets attach only to real profile experience rows.
"""

import re
from dataclasses import dataclass, field

from jinja2 import Environment, PackageLoader

from jobot.models.domain import UserProfile

TEMPLATE_NAMES = ("default", "modern", "classic")

_LATEX_SPECIALS = re.compile(r"([\\{}$&#^_%~])")


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters for safe template interpolation."""
    if not text:
        return ""
    return _LATEX_SPECIALS.sub(r"\\\1", text)


def _jinja_env() -> Environment:
    env = Environment(
        loader=PackageLoader("jobot.documents", "templates"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["latex"] = escape_latex
    return env


@dataclass
class ResumeEntry:
    title: str
    subtitle: str = ""
    period: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class ResumeSection:
    heading: str
    entries: list[ResumeEntry] = field(default_factory=list)


@dataclass
class ResumeData:
    name: str
    contact: str
    linkedin: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    sections: list[ResumeSection] = field(default_factory=list)

    def to_plain_text(self) -> str:
        """Render resume as single-column ATS plain text."""
        lines = [
            f"=== {self.name.upper()} ===",
            self.contact,
        ]
        if self.linkedin:
            lines.append(f"LinkedIn: {self.linkedin}")
        if self.summary:
            lines.extend(["", self.summary])
        if self.skills:
            lines.extend(["", "--- SKILLS SUMMARY ---", ", ".join(self.skills)])
        for section in self.sections:
            lines.extend(["", f"--- {section.heading.upper()} ---"])
            for entry in section.entries:
                header = f"* {entry.title}"
                if entry.subtitle:
                    header += f" at {entry.subtitle}"
                if entry.period:
                    header += f" ({entry.period})"
                lines.append(header)
                for bullet in entry.bullets:
                    lines.append(f"  - {bullet}")
        return "\n".join(lines)


def compile_resume_data(
    profile: UserProfile,
    summary: str | None = None,
    skills: list[str] | None = None,
    experience_bullets: dict[str, list[str]] | None = None,
) -> ResumeData:
    """Compile profile facts into ResumeData.

    `experience_bullets` maps "company|title" -> bullet lines; bullets are
    attached only when the (title, company) pair exists in the profile
    (grounding: no fabricated experience rows).
    """
    p = profile.personal_info
    contact_parts = [p.email, p.phone]
    if p.location_city:
        location = ", ".join(x for x in (p.location_city, p.location_country) if x)
        if location:
            contact_parts.append(location)
    contact = " | ".join(x for x in contact_parts if x)

    sections: list[ResumeSection] = []
    if profile.experiences:
        exp_entries: list[ResumeEntry] = []
        for exp in profile.experiences:
            period = f"{exp.start_date} - {exp.end_date or 'Present'}"
            key = f"{exp.company}|{exp.title}"
            bullets = list((experience_bullets or {}).get(key, []))
            if exp.description and not bullets:
                bullets = [exp.description]
            exp_entries.append(
                ResumeEntry(title=exp.title, subtitle=exp.company, period=period, bullets=bullets)
            )
        sections.append(ResumeSection(heading="WORK EXPERIENCE", entries=exp_entries))

    if profile.education:
        edu_entries = [
            ResumeEntry(
                title=f"{edu.degree} in {edu.field_of_study}".strip(),
                subtitle=edu.institution,
                period=str(edu.start_year),
            )
            for edu in profile.education
        ]
        sections.append(ResumeSection(heading="EDUCATION", entries=edu_entries))

    if not summary:
        summary = (
            f"Notice period: {profile.compensation.notice_period_days} days."
            if profile.compensation.notice_period_days
            else ""
        )

    return ResumeData(
        name=f"{p.first_name} {p.last_name}".strip(),
        contact=contact,
        linkedin=p.linkedin_url or "",
        summary=summary,
        skills=list(skills or profile.skills),
        sections=sections,
    )


def render_tex(data: ResumeData, template: str = "default") -> str:
    """Render ResumeData through a Jinja2 LaTeX template."""
    if template not in TEMPLATE_NAMES:
        raise ValueError(f"Unknown template '{template}'. Choose from {TEMPLATE_NAMES}.")
    env = _jinja_env()
    template_obj = env.get_template(f"{template}.tex.j2")
    return template_obj.render(data=data)
