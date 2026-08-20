import html
import logging
import tracemalloc
from pathlib import Path

from jobot.documents.ats import AtsScore, AtsScorer
from jobot.documents.compiler import compile_resume_data
from jobot.documents.engines import PdfRenderer, get_renderer
from jobot.models.domain import UserProfile

logger = logging.getLogger(__name__)

# Phase P3: peak-RSS budget for a single resume PDF. tracemalloc measures
# Python heap allocations (not native shared libs) so this is a lower
# bound, but it is enough to catch a "story list blew up to 100MB"
# regression. Typical resume PDFs render with <2MB of Python heap.
_PEAK_MEMORY_BUDGET_MB = 50.0


class ResumeExporter:
    """
    ATS Resume Compiler & Exporter (Layer J).
    Compiles candidate profile facts into clean, single-page ATS-optimized Text and HTML resumes.
    """

    def compile_text_resume(self, profile: UserProfile) -> str:
        """Compile profile into plain text ATS resume."""
        p = profile.personal_info
        c = profile.compensation

        lines = [
            f"=== {p.first_name.upper()} {p.last_name.upper()} ===",
            f"Email: {p.email} | Phone: {p.phone}",
            f"Location: {p.location_city}, {p.location_state}, {p.location_country}",
            f"LinkedIn: {p.linkedin_url or 'N/A'}",
            "",
            "--- SKILLS SUMMARY ---",
            ", ".join(profile.skills),
            "",
            "--- PROFESSIONAL OVERVIEW ---",
            f"Target Roles: {profile.custom_qa_answers.get('Target Titles', 'Software Developer')}",
            f"Experience: {profile.custom_qa_answers.get('Years of Experience', '1')} Years",
            f"Notice Period: {c.notice_period_days} Days (Immediate)",
            "",
        ]

        if profile.experiences:
            lines.append("--- WORK EXPERIENCE ---")
            for exp in profile.experiences:
                lines.append(
                    f"* {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})"
                )
                if exp.description:
                    lines.append(f"  {exp.description}")
            lines.append("")

        if profile.education:
            lines.append("--- EDUCATION ---")
            for edu in profile.education:
                lines.append(
                    f"* {edu.degree} in {edu.field_of_study} - {edu.institution} ({edu.start_year})"
                )

        return "\n".join(lines)

    def compile_html_resume(self, profile: UserProfile) -> str:
        """Compile profile into single-page styled HTML resume for PDF rendering."""
        p = profile.personal_info
        first_name = html.escape(str(p.first_name))
        last_name = html.escape(str(p.last_name))
        email = html.escape(str(p.email))
        phone = html.escape(str(p.phone))
        city = html.escape(str(p.location_city))
        country = html.escape(str(p.location_country))
        linkedin = html.escape(str(p.linkedin_url or "N/A"))
        skills_html = "".join(
            [f"<span class='tag'>{html.escape(str(s))}</span>" for s in profile.skills]
        )

        html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Resume - {first_name} {last_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; line-height: 1.5; }}
  h1 {{ margin-bottom: 5px; color: #111; }}
  .contact {{ color: #555; margin-bottom: 20px; font-size: 14px; }}
  .section-title {{ font-size: 16px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 4px; margin-top: 20px; }}
  .tag {{ display: inline-block; background: #f0f0f0; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
  <h1>{first_name} {last_name}</h1>
  <div class="contact">
    {email} | {phone} | {city}, {country}<br>
    LinkedIn: {linkedin}
  </div>

  <div class="section-title">SKILLS</div>
  <div style="margin-top: 8px;">{skills_html}</div>

  <div class="section-title">SUMMARY</div>
  <p>Notice Period: {profile.compensation.notice_period_days} Days | Expected CTC: {f"₹{profile.compensation.expected_ctc_inr:,.0f}" if profile.compensation.expected_ctc_inr is not None else "Negotiable"}</p>
</body>
</html>"""
        return html_doc

    def export_resume_files(self, profile: UserProfile, output_dir: Path | None = None) -> Path:
        """Export text and HTML resume files to disk."""
        if output_dir is None:
            output_dir = Path.home() / ".jobot" / "resumes"
        output_dir.mkdir(parents=True, exist_ok=True)

        txt_file = output_dir / f"resume_{profile.profile_id}.txt"
        html_file = output_dir / f"resume_{profile.profile_id}.html"

        txt_file.write_text(self.compile_text_resume(profile), encoding="utf-8")
        html_file.write_text(self.compile_html_resume(profile), encoding="utf-8")

        logger.info(f"Exported ATS resume to: {txt_file}")
        return txt_file

    def export_resume_pdf(
        self,
        profile: UserProfile,
        template: str = "default",
        engine: str | None = None,
        output_dir: Path | None = None,
        summary: str | None = None,
        skills: list[str] | None = None,
        experience_bullets: dict[str, list[str]] | None = None,
        scorer: AtsScorer | None = None,
    ) -> tuple[Path, AtsScore]:
        """Render profile (optionally tailored) to PDF and score ATS parseability.

        engine: None (auto) | "latex" | "fallback". Returns (pdf_path, ats_score).

        Phase P3: tracks peak Python-heap allocations during the render via
        ``tracemalloc`` and logs a WARNING if the render exceeds the
        50MB budget. The render itself already streams to disk via
        ReportLab's canvas — the in-memory ``story`` list is the only
        unbounded growth vector and it is bounded by the size of the
        profile (a typical resume produces ~2MB of story, well under
        budget). This method enforces the contract so a future
        pathological input (e.g. a profile with 10,000 bullets) is
        caught by the budget check rather than silently OOMing the host.
        """
        if output_dir is None:
            output_dir = Path.home() / ".jobot" / "resumes"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Phase P3: tracemalloc reset + start before the render so the
        # peak measurement captures only this render's allocations.
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        try:
            data = compile_resume_data(
                profile,
                summary=summary,
                skills=skills,
                experience_bullets=experience_bullets,
            )
            renderer: PdfRenderer = get_renderer(engine)
            pdf_path = output_dir / f"resume_{profile.profile_id}_{template}.pdf"
            # The render itself streams the PDF to disk via the canvas —
            # the story list (built inside ``renderer.render``) is the
            # only in-memory growth vector.
            renderer.render(data, template, pdf_path)

            txt_path = output_dir / f"resume_{profile.profile_id}_{template}.txt"
            txt_path.write_text(data.to_plain_text(), encoding="utf-8")

            ats = (scorer or AtsScorer()).score_pdf(pdf_path)
        finally:
            snapshot_after = tracemalloc.take_snapshot()
            tracemalloc.stop()

        # Phase P3: compute the peak-stat difference and log if over budget.
        # ``statistics`` compares the before/after snapshots; the top entry
        # is the largest single allocation block group.
        try:
            stats = snapshot_after.compare_to(snapshot_before, "lineno")
            peak_bytes = sum(stat.size_diff for stat in stats if stat.size_diff > 0)
            peak_mb = peak_bytes / (1024 * 1024)
            if peak_mb > _PEAK_MEMORY_BUDGET_MB:
                logger.warning(
                    "Resume PDF render peak memory %.1fMB exceeds budget %.1fMB "
                    "(profile_id=%s, template=%s) — review for pathological input.",
                    peak_mb,
                    _PEAK_MEMORY_BUDGET_MB,
                    profile.profile_id,
                    template,
                )
            else:
                logger.debug(
                    "Resume PDF render peak memory: %.1fMB (budget %.1fMB)",
                    peak_mb,
                    _PEAK_MEMORY_BUDGET_MB,
                )
        except Exception:  # noqa: BLE001 — best-effort measurement
            logger.debug("tracemalloc comparison failed; peak-memory metric skipped")

        logger.info(
            "Exported resume PDF %s (ATS score %.2f, %s)",
            pdf_path,
            ats.score,
            "PASS" if ats.passed else "FAIL",
        )
        return pdf_path, ats
