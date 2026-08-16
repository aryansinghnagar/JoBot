import logging
from pathlib import Path
from typing import Optional
from jobot.models.domain import UserProfile

logger = logging.getLogger(__name__)


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
                lines.append(f"* {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})")
                if exp.description:
                    lines.append(f"  {exp.description}")
            lines.append("")

        if profile.education:
            lines.append("--- EDUCATION ---")
            for edu in profile.education:
                lines.append(f"* {edu.degree} in {edu.field_of_study} - {edu.institution} ({edu.start_year})")

        return "\n".join(lines)

    def compile_html_resume(self, profile: UserProfile) -> str:
        """Compile profile into single-page styled HTML resume for PDF rendering."""
        p = profile.personal_info
        skills_html = "".join([f"<span class='tag'>{s}</span>" for s in profile.skills])

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Resume - {p.first_name} {p.last_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; line-height: 1.5; }}
  h1 {{ margin-bottom: 5px; color: #111; }}
  .contact {{ color: #555; margin-bottom: 20px; font-size: 14px; }}
  .section-title {{ font-size: 16px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 4px; margin-top: 20px; }}
  .tag {{ display: inline-block; background: #f0f0f0; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
  <h1>{p.first_name} {p.last_name}</h1>
  <div class="contact">
    {p.email} | {p.phone} | {p.location_city}, {p.location_country}<br>
    LinkedIn: {p.linkedin_url or 'N/A'}
  </div>

  <div class="section-title">SKILLS</div>
  <div style="margin-top: 8px;">{skills_html}</div>

  <div class="section-title">SUMMARY</div>
  <p>Notice Period: {profile.compensation.notice_period_days} Days | Expected CTC: {f'₹{profile.compensation.expected_ctc_inr:,.0f}' if profile.compensation.expected_ctc_inr is not None else 'Negotiable'}</p>
</body>
</html>"""
        return html

    def export_resume_files(self, profile: UserProfile, output_dir: Optional[Path] = None) -> Path:
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
