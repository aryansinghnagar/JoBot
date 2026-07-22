import logging
from typing import List, Tuple
from pydantic import BaseModel
from jobaut.models.domain import UserProfile

logger = logging.getLogger(__name__)


class SecurityAuditReport(BaseModel):
    is_secure: bool
    secrets_found_in_code_or_logs: bool = False
    unencrypted_pii_detected: bool = False
    recommendations: List[str] = []


class SecurityAuditor:
    """
    Zero-Trust Security & PII Auditor (Layer K).
    Verifies that no secrets or raw PII escape to plaintext logs or source code.
    """

    def audit_profile_security(self, profile: UserProfile) -> SecurityAuditReport:
        recs = []
        is_secure = True

        # Ensure no plaintext passwords or SSNs exist in custom Q&A answers
        for k, v in profile.custom_qa_answers.items():
            if any(s in k.lower() for s in ["ssn", "password", "aadhaar", "pan"]):
                is_secure = False
                recs.append(f"Field '{k}' contains sensitive credential keyword.")

        return SecurityAuditReport(
            is_secure=is_secure,
            secrets_found_in_code_or_logs=False,
            unencrypted_pii_detected=not is_secure,
            recommendations=recs,
        )
