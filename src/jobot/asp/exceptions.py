from jobot.models.domain import PipelinePhase


class PipelinePhaseFailure(Exception):
    """Raised when an ASP pipeline phase fails its Definition of Done (DoD)."""

    def __init__(self, phase: PipelinePhase, reason: str):
        self.phase = phase
        self.reason = reason
        super().__init__(f"ASP Phase '{phase.value}' failed DoD: {reason}")


class DoDViolation(Exception):
    """Raised when a specific Definition of Done gate rule is violated."""
    pass
