"""Tests for DOCX XML parser XXE safety and text extraction."""

import io
import zipfile
from pathlib import Path

from jobot.documents.importer import ResumeImporter


def create_docx_bytes(document_xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def test_docx_text_extraction(tmp_path: Path):
    doc_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p><w:r><w:t>Jane Doe</w:t></w:r></w:p>
            <w:p><w:r><w:t>Senior Engineer</w:t></w:r></w:p>
        </w:body>
    </w:document>
    """
    docx_file = tmp_path / "resume.docx"
    docx_file.write_bytes(create_docx_bytes(doc_xml))

    importer = ResumeImporter()
    text = importer._extract_docx_text(docx_file)
    assert "Jane Doe" in text
    assert "Senior Engineer" in text


def test_docx_corrupt_fallback(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.docx"
    corrupt_file.write_text("Not a real zip or docx content", encoding="utf-8")

    importer = ResumeImporter()
    text = importer._extract_docx_text(corrupt_file)
    assert "Not a real zip" in text
