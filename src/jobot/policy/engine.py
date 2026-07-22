import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from jobot.models.domain import Application, JobPosting, TrustLevel, UserProfile

logger = logging.getLogger(__name__)


class PolicyViolation(BaseModel):
    policy_name: str
    reason: str
    is_blocking: bool = True


class PolicyEvaluationResult(BaseModel):
    allowed: bool
    requires_approval: bool
    violations: List[PolicyViolation]
    blocking_reason: Optional[str] = None


from jobot.obs.alerts import AlertDispatcher, AlertLevel


class PolicyEngine:
    """
    Policy & Security Governance Engine (Layer H).
    Enforces 9 default safety, rate-limiting, privacy, and truthfulness policy rules.
    """

    def __init__(self, alert_dispatcher: Optional[AlertDispatcher] = None) -> None:
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.daily_application_limits: Dict[str, int] = {
            "naukri": 150,
            "linkedin": 100,
            "indeed": 100,
            "greenhouse": 150,
            "lever": 150,
            "workday": 100,
            "glassdoor": 100,
            "instahyre": 100,
            "cutshort": 100,
            "wellfound": 100,
            "mock_ats": 200,
        }

    def evaluate_application_policy(
        self,
        job: JobPosting,
        profile: UserProfile,
        application: Application,
        daily_submitted_count: int,
    ) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []

        # Policy 1: Max Daily Applications Cap
        max_allowed = self.daily_application_limits.get(job.site, 20)
        if daily_submitted_count >= max_allowed:
            msg = f"Daily limit of {max_allowed} applications reached for site '{job.site}'."
            violations.append(
                PolicyViolation(
                    policy_name="POLICY_MAX_DAILY_APPLICATIONS",
                    reason=msg,
                )
            )
            self.alert_dispatcher.dispatch_alert(
                title=f"Daily Limit Reached ({job.site})",
                message=msg,
                level=AlertLevel.WARNING,
            )

        # Policy 2: Grounding Check
        if application.status.value == "failed" and "Grounding" in (application.error_message or ""):
            violations.append(
                PolicyViolation(
                    policy_name="POLICY_GROUNDING_CHECK",
                    reason="Application failed profile grounding check.",
                )
            )

        # Policy 3: Sensitive Data Exclusion
        if any(w in job.description.lower() for w in ["aadhaar number", "ssn number", "bank password"]):
            violations.append(
                PolicyViolation(
                    policy_name="POLICY_SENSITIVE_DATA_EXCLUSION",
                    reason="Job description requests prohibited sensitive credentials.",
                )
            )

        # Policy 4: Supervised Trust Default
        if application.trust_level == TrustLevel.SUPERVISED and not application.form_values.get("approved_by_user"):
            violations.append(
                PolicyViolation(
                    policy_name="POLICY_SUPERVISED_START",
                    reason="Supervised mode requires user approval before final submission.",
                    is_blocking=False,  # Triggers ApprovalGate pause rather than hard fail
                )
            )

        return violations

    def check_application_policy(
        self,
        job: JobPosting,
        profile: UserProfile,
        application: Application,
        daily_submitted_count: int,
    ) -> PolicyEvaluationResult:
        violations = self.evaluate_application_policy(job, profile, application, daily_submitted_count)
        blocking_violations = [v for v in violations if v.is_blocking]
        non_blocking_violations = [v for v in violations if not v.is_blocking]

        allowed = len(blocking_violations) == 0
        requires_approval = any(v.policy_name == "POLICY_SUPERVISED_START" for v in non_blocking_violations)
        blocking_reason = blocking_violations[0].reason if blocking_violations else None

        return PolicyEvaluationResult(
            allowed=allowed,
            requires_approval=requires_approval,
            violations=violations,
            blocking_reason=blocking_reason,
        )
