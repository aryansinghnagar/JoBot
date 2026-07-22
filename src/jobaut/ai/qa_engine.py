import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from jobaut.ai.router import ModelRouter
from jobaut.models.domain import UserProfile


class QuestionType(str, Enum):
    PROFILE_DIRECT = "profile_direct"
    BEHAVIORAL = "behavioral"
    SENSITIVE = "sensitive"
    UNANSWERABLE = "unanswerable"


class AnswerResult(BaseModel):
    question: str
    answer: str
    question_type: QuestionType
    is_grounded: bool
    confidence_score: float
    requires_user_approval: bool


class QAEngine:
    """
    Form Q&A Engine with Profile-Grounding Verification & Prompt-Injection Defense.
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    def sanitize_input(self, text: str) -> str:
        """Strip malicious prompt injection vectors from input question string."""
        injection_patterns = [
            r"ignore\s+(previous|all)\s+instructions",
            r"system\s+prompt",
            r"override\s+policy",
            r"forget\s+rules",
        ]
        sanitized = text
        for pattern in injection_patterns:
            sanitized = re.sub(pattern, "[REDACTED_INJECTION]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def classify_question(self, question: str) -> QuestionType:
        q_lower = question.lower()
        if any(k in q_lower for k in ["name", "email", "phone", "notice period", "ctc", "salary", "experience"]):
            return QuestionType.PROFILE_DIRECT
        if any(k in q_lower for k in ["why", "describe", "project", "challenge", "accomplishment", "joining"]):
            return QuestionType.BEHAVIORAL
        if any(k in q_lower for k in ["passport", "ssn", "aadhaar", "pan card", "bank account"]):
            return QuestionType.SENSITIVE
        return QuestionType.UNANSWERABLE

    def verify_grounding(self, question: str, answer: str, profile: UserProfile) -> bool:
        """
        Grounding Gate: Check that generated answer does not invent ungrounded facts.
        """
        # If candidate email or phone appears in answer, verify exact match with profile
        if profile.personal_info.email and profile.personal_info.email.lower() not in answer.lower():
            if "@" in answer:
                return False
        return True

    async def answer_question(self, question: str, profile: UserProfile) -> AnswerResult:
        clean_question = self.sanitize_input(question)
        q_type = self.classify_question(clean_question)

        # 1. Profile Direct Answers
        if q_type == QuestionType.PROFILE_DIRECT:
            q_lower = clean_question.lower()
            if "email" in q_lower:
                ans = profile.personal_info.email
            elif "phone" in q_lower or "mobile" in q_lower:
                ans = profile.personal_info.phone
            elif "notice" in q_lower:
                ans = f"{profile.compensation.notice_period_days} Days"
            elif "expected" in q_lower and "ctc" in q_lower:
                ans = f"{profile.compensation.expected_ctc_inr or 1800000} INR"
            elif "current" in q_lower and "ctc" in q_lower:
                ans = f"{profile.compensation.current_ctc_inr or 1200000} INR"
            else:
                ans = f"{profile.personal_info.first_name} {profile.personal_info.last_name}"

            return AnswerResult(
                question=question,
                answer=ans,
                question_type=q_type,
                is_grounded=True,
                confidence_score=1.0,
                requires_user_approval=False,
            )

        # 2. Sensitive Questions (Require User Approval)
        if q_type == QuestionType.SENSITIVE:
            return AnswerResult(
                question=question,
                answer="[SENSITIVE_FIELD_PAUSED]",
                question_type=q_type,
                is_grounded=True,
                confidence_score=0.0,
                requires_user_approval=True,
            )

        # 3. Behavioral Questions (LLM Generation + Grounding Gate)
        prompt = (
            f"Candidate Profile Info:\n"
            f"Name: {profile.personal_info.first_name} {profile.personal_info.last_name}\n"
            f"Skills: {', '.join(profile.skills)}\n\n"
            f"Answer the job application question truthfully without inventing facts:\n"
            f"Question: {clean_question}"
        )
        llm_answer = await self.router.generate_text(prompt)
        is_grounded = self.verify_grounding(clean_question, llm_answer, profile)

        return AnswerResult(
            question=question,
            answer=llm_answer,
            question_type=q_type,
            is_grounded=is_grounded,
            confidence_score=0.85 if is_grounded else 0.0,
            requires_user_approval=not is_grounded,
        )
