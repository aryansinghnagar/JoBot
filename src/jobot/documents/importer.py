"""Resume PDF/Text Ingestion and Profile Synthesizer (UC-25).

Parses candidate resumes into structured UserProfile objects and populates
the CandidateTruthStore with immutable ground truth facts.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from jobot.ai.candidate_truth import CandidateTruthStore
from jobot.ai.router import ModelRouter
from jobot.ai.skill_extractor import SkillExtractor
from jobot.config.manager import ConfigManager
from jobot.documents.ats import extract_pdf_text
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import (
    CompensationDetails,
    Education,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)
from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9._%+-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?[\d\s\-().]{10,}")


class ResumeImporter:
    """Ingests PDF/Text resumes and converts them into structured UserProfiles."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        db: Optional[DatabaseManager] = None,
        config: Optional[ConfigManager] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.db = db or DatabaseManager()
        self.truth_store = CandidateTruthStore(self.db)
        self.config = config or ConfigManager()
        self.skill_extractor = SkillExtractor()

    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from PDF, Word (.docx), or plain text files."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Resume file not found: {p}")

        ext = p.suffix.lower()
        if ext == ".pdf":
            return extract_pdf_text(p)
        elif ext == ".docx":
            return self._extract_docx_text(p)
        return p.read_text(encoding="utf-8", errors="ignore")

    def _extract_docx_text(self, path: Path) -> str:
        """Extract text from a Microsoft Word .docx file using standard library zip and xml."""
        import xml.etree.ElementTree as ET
        import zipfile

        try:
            with zipfile.ZipFile(path) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                nodes = tree.findall(".//w:t", namespaces)
                texts = [n.text for n in nodes if n.text]
                return "\n".join(texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse .docx file (%s); falling back to raw read", exc)
            return path.read_text(encoding="utf-8", errors="ignore")

    async def parse_resume_text(self, text: str, profile_id: str = "default") -> UserProfile:
        """Parse raw resume text into a structured UserProfile."""
        prompt = (
            "You are an expert resume parser. Extract structured candidate information "
            "from the following resume text into a JSON object matching this schema:\n\n"
            "{\n"
            '  "personal_info": {\n'
            '    "first_name": "...",\n'
            '    "last_name": "...",\n'
            '    "email": "...",\n'
            '    "phone": "...",\n'
            '    "location_city": "...",\n'
            '    "location_country": "India"\n'
            "  },\n"
            '  "skills": ["skill1", "skill2", ...],\n'
            '  "experiences": [\n'
            "    {\n"
            '      "company": "...",\n'
            '      "title": "...",\n'
            '      "start_date": "YYYY-MM",\n'
            '      "end_date": "YYYY-MM" or null,\n'
            '      "is_current": false,\n'
            '      "description": "...",\n'
            '      "technologies": ["tech1", ...]\n'
            "    }\n"
            "  ],\n"
            '  "education": [\n'
            "    {\n"
            '      "institution": "...",\n'
            '      "degree": "...",\n'
            '      "field_of_study": "...",\n'
            '      "start_year": 2018,\n'
            '      "end_year": 2022\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Resume Text:\n{text[:4000]}"
        )

        try:
            res_text = await self.router.generate_text(
                prompt,
                task="resume_parsing",
                temperature=0.1,
                max_tokens=2048,
            )
            if not res_text.startswith(DEGRADATION_TEXT):
                start = res_text.find("{")
                end = res_text.rfind("}")
                if start != -1 and end > start:
                    data = json.loads(res_text[start : end + 1])
                    return self._build_profile_from_data(data, profile_id, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM resume parsing failed (%s); falling back to rule-based parser", exc)

        return self._heuristic_parse(text, profile_id)

    def _build_profile_from_data(
        self, data: Dict[str, Any], profile_id: str, raw_text: str
    ) -> UserProfile:
        pi_data = data.get("personal_info", {})
        personal_info = PersonalInfo(
            first_name=str(pi_data.get("first_name", "")),
            last_name=str(pi_data.get("last_name", "")),
            email=str(pi_data.get("email", "")),
            phone=str(pi_data.get("phone", "")),
            location_city=str(pi_data.get("location_city", "")),
            location_country=str(pi_data.get("location_country", "India")),
        )

        skills = [str(s).strip() for s in data.get("skills", []) if str(s).strip()]
        # Supplement skills using SkillExtractor
        extracted_skills = self.skill_extractor.extract_skills_sync(raw_text)
        for es in extracted_skills:
            if es not in skills:
                skills.append(es)

        experiences: list[WorkExperience] = []
        for exp in data.get("experiences", []):
            experiences.append(
                WorkExperience(
                    company=str(exp.get("company", "")),
                    title=str(exp.get("title", "")),
                    start_date=str(exp.get("start_date", "2020-01")),
                    end_date=exp.get("end_date"),
                    is_current=bool(exp.get("is_current", False)),
                    description=str(exp.get("description", "")),
                    technologies=[str(t) for t in exp.get("technologies", [])],
                )
            )

        education: list[Education] = []
        for edu in data.get("education", []):
            education.append(
                Education(
                    institution=str(edu.get("institution", "")),
                    degree=str(edu.get("degree", "")),
                    field_of_study=str(edu.get("field_of_study", "")),
                    start_year=int(edu.get("start_year", 2018)),
                    end_year=int(edu["end_year"]) if edu.get("end_year") else None,
                )
            )

        return UserProfile(
            profile_id=profile_id,
            personal_info=personal_info,
            skills=skills,
            experiences=experiences,
            education=education,
            compensation=CompensationDetails(),
        )

    def _heuristic_parse(self, text: str, profile_id: str) -> UserProfile:
        """Deterministic regex-based fallback for offline/air-gapped ingestion."""
        email_match = _EMAIL_RE.search(text)
        email = email_match.group(0) if email_match else ""

        phone_match = _PHONE_RE.search(text)
        phone = phone_match.group(0).strip() if phone_match else ""

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        name_line = lines[0] if lines else "Candidate"
        name_parts = name_line.split()
        first_name = name_parts[0] if name_parts else "Candidate"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        skills = self.skill_extractor.extract_skills_sync(text)

        return UserProfile(
            profile_id=profile_id,
            personal_info=PersonalInfo(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
            ),
            skills=skills,
            experiences=[],
            education=[],
            compensation=CompensationDetails(),
        )

    async def import_and_seed(
        self, file_path: Path, profile_id: str = "default"
    ) -> tuple[UserProfile, int]:
        """Ingest resume file, construct UserProfile, and seed CandidateTruthStore."""
        text = self.extract_text_from_file(file_path)
        profile = await self.parse_resume_text(text, profile_id=profile_id)
        facts = self.truth_store.seed_from_profile(profile)
        return profile, len(facts)


__all__ = ["ResumeImporter"]
