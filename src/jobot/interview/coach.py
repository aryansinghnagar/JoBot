"""STAR-method answer coach + multi-turn mock interviewer.

LLM-scored feedback with a deterministic rule-based fallback (no live LLM
dependency in degraded mode, per the project's degradation doctrine).
"""

import json
import re
from typing import Dict, List, Optional

from pydantic import BaseModel

from jobot.ai.qa_engine import QAEngine
from jobot.interview.banks import InterviewQuestion, QuestionBank
from jobot.interview.sessions import InterviewSession, InterviewTurn, SessionStore, new_session
from jobot.llm.router import DEGRADATION_TEXT, ModelRouter
from jobot.models.domain import UserProfile

STAR_MARKERS = {
    "situation": ["situation", "context", "background", "at the time", "was working"],
    "task": ["task", "goal", "objective", "needed to", "had to", "assigned"],
    "action": ["action", "i did", "i built", "i implemented", "i designed", "i led", "i wrote"],
    "result": [
        "result",
        "outcome",
        "impact",
        "improved",
        "reduced",
        "increased",
        "shipped",
        "led to",
    ],
}


class STARFeedback(BaseModel):
    star_score: float
    scores: Dict[str, float]
    feedback: str
    grounded: bool = True


def _rule_based_score(answer: str) -> STARFeedback:
    text = answer.lower()
    scores = {}
    for component, markers in STAR_MARKERS.items():
        scores[component] = 1.0 if any(m in text for m in markers) else 0.0
    length_bonus = min(1.0, len(answer.split()) / 40.0)
    star_score = round((sum(scores.values()) / 4.0) * 0.7 + length_bonus * 0.3, 3)
    missing = [c for c, v in scores.items() if v == 0.0]
    if not missing:
        feedback = "Complete STAR structure detected. Good coverage of all four components."
    else:
        feedback = (
            f"Missing STAR components: {', '.join(missing)}. "
            "Add the missing elements to strengthen the answer."
        )
    return STARFeedback(star_score=star_score, scores=scores, feedback=feedback)


class STARCoach:
    """Scores candidate answers against the STAR rubric via LLM or fallback."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        qa: Optional[QAEngine] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.qa = qa or QAEngine(self.router)

    async def coach_answer(
        self,
        question: InterviewQuestion,
        answer: str,
        profile: UserProfile,
    ) -> STARFeedback:
        grounded = self.qa.verify_grounding(question.text, answer, profile)
        prompt = (
            "Score this interview answer using the STAR rubric "
            "(situation, task, action, result). "
            "Return strict JSON: "
            '{"scores": {"situation": 0-1, "task": 0-1, "action": 0-1, "result": 0-1}, '
            '"feedback": "one paragraph", "star_present": true/false}\n\n'
            f"Question: {question.text}\n\nAnswer: {answer}"
        )
        text = await self.router.generate_text(prompt, task="interview_coach")
        if not grounded:
            return STARFeedback(
                star_score=0.0,
                scores={c: 0.0 for c in STAR_MARKERS},
                feedback="Answer failed the profile-grounding gate; review for invented facts.",
                grounded=False,
            )
        if text.startswith(DEGRADATION_TEXT):
            return _rule_based_score(answer)
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return _rule_based_score(answer)
        scores = {c: float(parsed.get("scores", {}).get(c, 0.0)) for c in STAR_MARKERS}
        star_score = round(sum(scores.values()) / 4.0, 3)
        return STARFeedback(
            star_score=star_score,
            scores=scores,
            feedback=str(parsed.get("feedback", "")).strip() or "No feedback provided.",
        )


class MockInterviewer:
    """Multi-turn mock interview: question -> answer -> STAR feedback."""

    def __init__(
        self,
        bank: Optional[QuestionBank] = None,
        coach: Optional[STARCoach] = None,
        store: Optional[SessionStore] = None,
    ) -> None:
        self.bank = bank or QuestionBank()
        self.coach = coach or STARCoach()
        self.store = store or SessionStore()

    def start(self, track: str) -> InterviewSession:
        self.bank.questions(track)
        session = new_session(track)
        self.store.save(session)
        return session

    def next_question(self, session: InterviewSession) -> Optional[InterviewQuestion]:
        return self.bank.next_question(
            session.track,
            session.asked_ids,
            difficulty_ramp=len(session.turns) // 2,
        )

    async def answer(
        self,
        session: InterviewSession,
        answer_text: str,
        profile: UserProfile,
    ) -> InterviewTurn:
        question = self.next_question(session)
        if question is None:
            raise ValueError(f"no questions remaining in track '{session.track}'")
        feedback = await self.coach.coach_answer(question, answer_text, profile)
        turn = InterviewTurn(
            question_id=question.id,
            question_text=question.text,
            track=session.track,
            answer=answer_text,
            feedback=feedback.feedback,
            star_score=feedback.star_score,
        )
        session.turns.append(turn)
        session.asked_ids.append(question.id)
        self.store.save(session)
        return turn

    def complete(self, session: InterviewSession) -> InterviewSession:
        session.status = "completed"
        self.store.save(session)
        return session

    def average_score(self, session: InterviewSession) -> float:
        if not session.turns:
            return 0.0
        return round(sum(t.star_score for t in session.turns) / len(session.turns), 3)
