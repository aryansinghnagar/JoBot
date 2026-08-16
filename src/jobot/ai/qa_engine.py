import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from jobot.ai.candidate_truth import CandidateGroundingVerifier, CandidateTruthStore
from jobot.ai.router import ModelRouter
from jobot.models.domain import AnswerBankRecord, UserProfile
from jobot.storage.db import DatabaseManager


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
    Form Q&A Engine with Profile-Grounding Verification, Answer Bank, & Prompt-Injection Defense.
    """

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        db: Optional[DatabaseManager] = None,
        truth_store: Optional[CandidateTruthStore] = None,
    ):
        self.router = router or ModelRouter()
        self.db = db or DatabaseManager()
        self.truth_store = truth_store or CandidateTruthStore(self.db)
        self.grounding_verifier = CandidateGroundingVerifier(self.truth_store)

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
        if any(
            k in q_lower
            for k in ["name", "email", "phone", "notice period", "ctc", "salary", "experience"]
        ):
            return QuestionType.PROFILE_DIRECT
        if any(
            k in q_lower
            for k in ["why", "describe", "project", "challenge", "accomplishment", "joining"]
        ):
            return QuestionType.BEHAVIORAL
        if any(k in q_lower for k in ["passport", "ssn", "aadhaar", "pan card", "bank account"]):
            return QuestionType.SENSITIVE
        return QuestionType.UNANSWERABLE

    def verify_grounding(self, question: str, answer: str, profile: UserProfile) -> bool:
        """
        Grounding Gate: Check that generated answer does not invent ungrounded facts.
        """
        # 1. Direct PII check
        if (
            profile.personal_info.email
            and profile.personal_info.email.lower() not in answer.lower()
        ):
            if "@" in answer:
                return False

        facts = self.truth_store.get_facts(profile_id=profile.profile_id or "default")
        if not facts:
            facts = self.truth_store.seed_from_profile(profile)

        # 2. Comprehensive Candidate Grounding Verifier
        result = self.grounding_verifier.verify_text(
            answer, facts=facts, profile_id=profile.profile_id or "default"
        )
        return result.passed

    async def answer_question(self, question: str, profile: UserProfile) -> AnswerResult:
        clean_question = self.sanitize_input(question)
        q_type = self.classify_question(clean_question)
        p_id = profile.profile_id or "default"
        q_hash = hashlib.sha256(clean_question.lower().encode("utf-8")).hexdigest()

        # 0. Check custom QA answers or persistent Answer Bank first (UC-26)
        if clean_question in profile.custom_qa_answers:
            ans = profile.custom_qa_answers[clean_question]
            return AnswerResult(
                question=question,
                answer=ans,
                question_type=q_type,
                is_grounded=True,
                confidence_score=1.0,
                requires_user_approval=False,
            )

        saved_answer = self.db.get_answer_bank_entry(p_id, q_hash)
        if saved_answer:
            self.db.record_answer_bank_use(p_id, q_hash)
            return AnswerResult(
                question=question,
                answer=saved_answer.answer,
                question_type=q_type,
                is_grounded=True,
                confidence_score=0.95,
                requires_user_approval=False,
            )

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
        # Ensure truth store is seeded for candidate
        self.truth_store.seed_from_profile(profile)

        prompt = (
            f"Candidate Profile Info:\n"
            f"Name: {profile.personal_info.first_name} {profile.personal_info.last_name}\n"
            f"Skills: {', '.join(profile.skills)}\n\n"
            f"Answer the job application question truthfully without inventing facts:\n"
            f"Question: {clean_question}"
        )
        llm_answer = await self.router.generate_text(prompt)
        is_grounded = self.verify_grounding(clean_question, llm_answer, profile)

        if is_grounded:
            # Save verified answer in Answer Bank for future re-use
            self.db.save_answer_bank_entry(
                AnswerBankRecord(
                    profile_id=p_id,
                    question_hash=q_hash,
                    question_text=clean_question,
                    answer=llm_answer,
                    source="llm_grounded",
                    used_count=1,
                    last_used_at=datetime.now(timezone.utc),
                )
            )

        return AnswerResult(
            question=question,
            answer=llm_answer,
            question_type=q_type,
            is_grounded=is_grounded,
            confidence_score=0.85 if is_grounded else 0.0,
            requires_user_approval=not is_grounded,
        )
