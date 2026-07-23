import json
import re
from typing import List, Optional
from jobot.ai.router import ModelRouter


class SkillExtractor:
    """
    LLM-Powered Skill Extractor with Keyword Fallback (Layer 6).
    Extracts normalized technical and domain skills from raw job description text.
    """

    COMMON_TECH_KEYWORDS = [
        "python", "java", "c++", "c#", "golang", "go", "rust", "typescript", "javascript",
        "react", "angular", "vue", "node.js", "express", "fastapi", "flask", "django",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "git", "ci/cd", "jenkins", "github actions", "spark", "hadoop", "airflow",
        "machine learning", "deep learning", "nlp", "llm", "pytorch", "tensorflow",
        "scikit-learn", "pandas", "numpy", "system design", "microservices", "rest api", "graphql"
    ]

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    async def extract_skills(self, description: str) -> List[str]:
        """Extract and normalize technical skills from job description text."""
        if not description or len(description.strip()) < 10:
            return []

        # Attempt LLM extraction first
        try:
            prompt = (
                f"Extract technical skills, tools, and languages from the job description below.\n"
                f"Return ONLY a JSON array of strings, e.g. [\"Python\", \"FastAPI\", \"PostgreSQL\"]. No explanation.\n\n"
                f"Job Description:\n{description[:2000]}"
            )
            raw_response = await self.router.generate_text(prompt)

            if raw_response and not raw_response.startswith("[LLM_UNAVAILABLE]"):
                json_str = raw_response.strip()
                if json_str.startswith("```"):
                    lines = json_str.splitlines()
                    json_str = "\n".join([l for l in lines if not l.startswith("```")])
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    return self._normalize_skills([str(s) for s in parsed])
        except Exception:
            pass

        # Fallback: Keyword pattern matching
        return self._rule_based_extraction(description)

    def _normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize skills: strip whitespace, remove empty, deduplicate preserving order."""
        seen = set()
        normalized = []
        for s in skills:
            clean = s.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                normalized.append(clean)
        return normalized

    def _rule_based_extraction(self, description: str) -> List[str]:
        """Rule-based keyword matching fallback when LLM is unavailable."""
        extracted = []
        lower_desc = description.lower()

        for kw in self.COMMON_TECH_KEYWORDS:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, lower_desc):
                extracted.append(kw.title() if len(kw) <= 4 else kw.capitalize())

        return self._normalize_skills(extracted)
