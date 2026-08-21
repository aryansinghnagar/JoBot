"""Unit tests for ResumeImporter and CLI command (UC-25)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobot.cli.main import app
from jobot.documents.importer import ResumeImporter
from jobot.models.domain import UserProfile
from jobot.storage.db import DatabaseManager

runner = CliRunner()

SAMPLE_RESUME_TEXT = """
Alex Morgan
Email: alex.morgan@example.com
Phone: +1-555-0100
Location: San Francisco, CA, USA

EDUCATION
State University - B.S. in Computer Science (2018 - 2022)

EXPERIENCE
TechCorp - Senior Backend Engineer (2022-06 - Present)
* Built high-throughput async distributed streaming pipelines using Python, FastAPI, Docker, and PostgreSQL.
* Optimized Redis caching layer reducing p99 latency by 45%.

SKILLS
Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, Microservices, Git
"""


@pytest.mark.asyncio
async def test_resume_importer_text_parsing(tmp_path: Path):
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text(SAMPLE_RESUME_TEXT, encoding="utf-8")

    db = DatabaseManager(tmp_path / "test_import.db")
    importer = ResumeImporter(db=db)

    profile, facts_count = await importer.import_and_seed(resume_file, profile_id="test_candidate")
    assert isinstance(profile, UserProfile)
    assert profile.personal_info.email == "alex.morgan@example.com"
    assert facts_count > 0

    facts = db.list_candidate_facts(profile_id="test_candidate")
    assert len(facts) == facts_count
    assert any(f.fact_value == "alex.morgan@example.com" for f in facts)


def test_import_resume_cli(tmp_path: Path):
    resume_file = tmp_path / "test_cv.txt"
    resume_file.write_text(SAMPLE_RESUME_TEXT, encoding="utf-8")

    result = runner.invoke(app, ["import-resume", str(resume_file), "--no-save"])
    assert result.exit_code == 0
    assert "Ingested candidate profile" in result.stdout


@pytest.mark.asyncio
async def test_resume_importer_docx_parsing(tmp_path: Path):
    import zipfile

    docx_path = tmp_path / "resume.docx"
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Alex Morgan</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Email: alex.morgan@example.com</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Skills: Python, FastAPI, Docker</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(docx_path, "w") as z:
        z.writestr("word/document.xml", xml_content)

    db = DatabaseManager(tmp_path / "test_docx.db")
    importer = ResumeImporter(db=db)
    extracted = importer.extract_text_from_file(docx_path)
    assert "Alex Morgan" in extracted
    assert "alex.morgan@example.com" in extracted

    profile, facts_count = await importer.import_and_seed(docx_path, profile_id="test_docx")
    assert profile.personal_info.email == "alex.morgan@example.com"
    assert facts_count > 0
