"""PDF renderers (Phase 3, T3.1).

Pluggable stack: `LuaLaTeXRenderer` (lualatex/xelatex per plan Chapter 13)
with a pure-python `FallbackPdfRenderer` (reportlab) used when no TeX engine
is installed. Both consume the same `ResumeData`, so content is identical
regardless of engine.
"""

import logging
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from jobot.documents.compiler import ResumeData, render_tex

logger = logging.getLogger(__name__)


def lualatex_available() -> bool:
    return shutil.which("lualatex") is not None


def xelatex_available() -> bool:
    return shutil.which("xelatex") is not None


def tex_engine_available() -> bool:
    return lualatex_available() or xelatex_available()


def pdftotext_available() -> bool:
    return shutil.which("pdftotext") is not None


class PdfRenderer(ABC):
    """Renders ResumeData into a PDF file."""

    name: str = "abstract"

    @abstractmethod
    def available(self) -> bool:
        """Whether this renderer can run on this machine."""

    @abstractmethod
    def render(self, data: ResumeData, template: str, out_path: Path) -> Path:
        """Render data to out_path; raises RuntimeError on failure."""


class LuaLaTeXRenderer(PdfRenderer):
    """Render the Jinja2 LaTeX template with lualatex/xelatex."""

    name = "lualatex"

    def available(self) -> bool:
        return tex_engine_available()

    def render(self, data: ResumeData, template: str, out_path: Path) -> Path:
        engine = shutil.which("lualatex") or shutil.which("xelatex")
        if not engine:
            raise RuntimeError("No LaTeX engine (lualatex/xelatex) found on PATH")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tex_source = render_tex(data, template)

        with tempfile.TemporaryDirectory(prefix="jobot_resume_") as tmp:
            workdir = Path(tmp)
            tex_file = workdir / "resume.tex"
            tex_file.write_text(tex_source, encoding="utf-8")
            result = subprocess.run(
                [engine, "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=180,
            )
            pdf_file = workdir / "resume.pdf"
            if result.returncode != 0 or not pdf_file.exists():
                raise RuntimeError(
                    f"LaTeX compilation failed (exit {result.returncode}): "
                    f"{(result.stdout + result.stderr)[-2000:]}"
                )
            shutil.copyfile(pdf_file, out_path)
        logger.info("Rendered resume PDF via %s: %s", Path(engine).name, out_path)
        return out_path


class FallbackPdfRenderer(PdfRenderer):
    """Pure-python reportlab renderer — always available, no system deps."""

    name = "reportlab"

    def available(self) -> bool:
        return True

    def render(self, data: ResumeData, template: str, out_path: Path) -> Path:
        # Template choice only affects the LaTeX flavor; the fallback keeps one
        # deterministic single-column layout (ATS-safe) for all templates.
        out_path.parent.mkdir(parents=True, exist_ok=True)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ResumeTitle", parent=styles["Title"], fontSize=17, spaceAfter=2
        )
        center_style = ParagraphStyle(
            "ResumeCenter", parent=styles["Normal"], alignment=1, fontSize=10, spaceAfter=2
        )
        heading_style = ParagraphStyle(
            "ResumeHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=3,
            borderPadding=0,
        )
        bullet_style = ParagraphStyle(
            "ResumeBullet", parent=styles["Normal"], fontSize=9.5, leftIndent=14, spaceAfter=2
        )
        entry_style = ParagraphStyle("ResumeEntry", parent=styles["Normal"], fontSize=10.5)

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )
        story: List[Any] = []

        def esc(text: str) -> str:
            return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        story.append(Paragraph(f"<b>{esc(data.name)}</b>", title_style))
        if data.contact:
            story.append(Paragraph(esc(data.contact), center_style))
        if data.linkedin:
            story.append(Paragraph(f"LinkedIn: {esc(data.linkedin)}", center_style))

        if data.summary:
            story.append(Paragraph("<b>SUMMARY</b>", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.6))
            story.append(Paragraph(esc(data.summary), styles["Normal"]))
            story.append(Spacer(1, 4))

        story.append(Paragraph("<b>SKILLS</b>", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.6))
        if data.skills:
            story.append(Paragraph(esc(", ".join(data.skills)), styles["Normal"]))
            story.append(Spacer(1, 4))

        for section in data.sections:
            story.append(Paragraph(f"<b>{esc(section.heading.upper())}</b>", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.6))
            for entry in section.entries:
                line = f"<b>{esc(entry.title)}</b>"
                if entry.subtitle:
                    line += f" - <i>{esc(entry.subtitle)}</i>"
                if entry.period:
                    line += f" &nbsp;&nbsp; {esc(entry.period)}"
                story.append(Paragraph(line, entry_style))
                for bullet in entry.bullets:
                    story.append(Paragraph(f"- {esc(bullet)}", bullet_style))
                story.append(Spacer(1, 3))

        doc.build(story)
        logger.info("Rendered resume PDF via reportlab: %s", out_path)
        return out_path


def get_renderer(prefer: Optional[str] = None) -> PdfRenderer:
    """Resolve renderer: 'latex' | 'fallback' | None (auto: latex, else fallback)."""
    if prefer == "latex":
        if tex_engine_available():
            return LuaLaTeXRenderer()
        logger.warning("No LaTeX engine found; falling back to reportlab renderer")
        return FallbackPdfRenderer()
    if prefer == "fallback":
        return FallbackPdfRenderer()
    if tex_engine_available():
        return LuaLaTeXRenderer()
    return FallbackPdfRenderer()
