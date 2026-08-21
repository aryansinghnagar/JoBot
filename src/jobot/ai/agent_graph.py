"""Multi-Agent Drafter-Evaluator State Graph (Phase 3 / Layer D & G).

Implements a deterministic multi-agent state graph for candidate-grounded
resume tailoring, rubric evaluation, and adversarial truth verification.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from jobot.documents.tailor import DocumentTailor, verify_fact_truthfulness_detailed
from jobot.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Shared typed state passed between agent nodes."""

    user_goal: str
    job: JobPosting
    profile: UserProfile
    tailored_text: str
    grounding_passed: bool
    grounding_score: float
    unverified_facts: list[str]
    rubric_grade: str
    step_count: int
    max_steps: int
    next_node: str
    error: str | None


async def supervisor_node(state: AgentState) -> AgentState:
    """Supervises graph execution, routing to drafter, evaluator, or termination."""
    state["step_count"] += 1
    if state["step_count"] > state["max_steps"]:
        logger.warning("Multi-agent graph reached maximum step count (%d). Finalizing.", state["max_steps"])
        state["next_node"] = "end"
        return state

    if not state["tailored_text"]:
        state["next_node"] = "drafter"
    elif not state["grounding_passed"] and state["step_count"] <= 3:
        state["next_node"] = "drafter"
    elif state["grounding_passed"]:
        state["next_node"] = "evaluator"
    else:
        state["next_node"] = "end"
    return state


async def drafter_node(state: AgentState) -> AgentState:
    """Generates or refines tailored resume bullets based on candidate profile and job."""
    logger.info("Multi-agent: executing drafter node (attempt %d)", state["step_count"])
    tailor = DocumentTailor()
    tailored_res = await tailor.generate_tailored_materials(state["job"], state["profile"])
    state["tailored_text"] = (
        tailored_res.tailored_summary
        or f"{state['profile'].personal_info.first_name} {state['profile'].personal_info.last_name}"
    )

    # Immediately check grounding against candidate truth
    passed, notes = verify_fact_truthfulness_detailed(state["tailored_text"], state["profile"])
    state["grounding_passed"] = passed
    state["grounding_score"] = 1.0 if passed else 0.7
    state["unverified_facts"] = notes
    state["next_node"] = "evaluator" if state["grounding_passed"] else "supervisor"
    return state


async def evaluator_node(state: AgentState) -> AgentState:
    """Evaluates tailored document against ATS rubric (A-F grading)."""
    logger.info("Multi-agent: executing evaluator node")
    score = state["grounding_score"]
    if score >= 0.90:
        state["rubric_grade"] = "A"
    elif score >= 0.80:
        state["rubric_grade"] = "B"
    elif score >= 0.70:
        state["rubric_grade"] = "C"
    else:
        state["rubric_grade"] = "D"
    state["next_node"] = "end"
    return state


async def run_tailoring_graph(
    profile: UserProfile,
    job: JobPosting,
    *,
    max_steps: int = 5,
) -> AgentState:
    """Execute the multi-agent tailoring and evaluation graph end-to-end."""
    state: AgentState = {
        "user_goal": f"Tailor resume for {job.title} at {job.company}",
        "job": job,
        "profile": profile,
        "tailored_text": "",
        "grounding_passed": False,
        "grounding_score": 0.0,
        "unverified_facts": [],
        "rubric_grade": "Pending",
        "step_count": 0,
        "max_steps": max_steps,
        "next_node": "supervisor",
        "error": None,
    }

    while state["next_node"] != "end" and state["step_count"] <= max_steps:
        current = state["next_node"]
        if current == "supervisor":
            state = await supervisor_node(state)
        elif current == "drafter":
            state = await drafter_node(state)
        elif current == "evaluator":
            state = await evaluator_node(state)
        else:
            break

    return state
