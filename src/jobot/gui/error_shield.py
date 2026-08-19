"""Humanized Error Shield & Translation Engine (Layer B/C).

Translates technical Python exceptions and adapter errors into plain-English,
actionable guidance for non-technical users while preserving structured diagnostics.
"""

from typing import Any


class HumanizedError:
    """Encapsulates a user-friendly error with actionable next steps."""

    def __init__(
        self,
        user_message: str,
        action_hint: str,
        category: str = "general",
        technical_details: str | None = None,
        code: int = -32000,
    ):
        self.user_message = user_message
        self.action_hint = action_hint
        self.category = category
        self.technical_details = technical_details
        self.code = code

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.user_message,
            "data": {
                "user_message": self.user_message,
                "action_hint": self.action_hint,
                "category": self.category,
                "technical_details": self.technical_details,
            },
        }


def humanize_exception(exc: Exception) -> HumanizedError:
    """Convert any Python exception into a structured HumanizedError."""
    exc_type = type(exc).__name__
    exc_str = str(exc)

    # 1. ATS Adapter Capability Errors
    if "AdapterCapabilityError" in exc_type or "does not support direct submission" in exc_str:
        return HumanizedError(
            user_message="Automatic 1-click submission is not available for this job board yet.",
            action_hint="We have generated your tailored resume! Use 'Assisted Apply' to open the application link and copy your tailored summary with one click.",
            category="adapter_unsupported",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32001,
        )

    # 2. Missing Profile or Not Initialized
    if "Profile missing" in exc_str or "run 'jobot profile init'" in exc_str:
        return HumanizedError(
            user_message="No candidate profile found. Let's get you set up!",
            action_hint="Upload your resume or complete the quick setup wizard in the Profile tab.",
            category="missing_profile",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32002,
        )

    # 3. File Not Found (Resume, Template, Artifact)
    if isinstance(exc, FileNotFoundError) or "Resume file not found" in exc_str:
        return HumanizedError(
            user_message="The selected file could not be found.",
            action_hint="Please check the file path or choose another document using the file picker.",
            category="file_not_found",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32003,
        )

    # 4. LLM API Key / Rate Limit Errors
    if "API key" in exc_str or "api_key" in exc_str or "unauthorized" in exc_str.lower():
        return HumanizedError(
            user_message="AI service connection failed. Your API key may be missing or expired.",
            action_hint="Check your AI settings in the Settings tab, or get a free Gemini API key in 60 seconds.",
            category="ai_auth_error",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32004,
        )

    if "429" in exc_str or "rate limit" in exc_str.lower() or "quota" in exc_str.lower():
        return HumanizedError(
            user_message="The AI provider is momentarily busy (rate limit reached).",
            action_hint="JoBot will automatically pause and retry in a moment. You can also switch to another AI provider in Settings.",
            category="rate_limit",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32005,
        )

    # 5. Missing Candidate Truth Facts
    if "MissingFactError" in exc_type or "missing fact" in exc_str.lower():
        return HumanizedError(
            user_message="The application requires information not found in your profile.",
            action_hint="Open the 'Approvals' tab to review and answer the screening question.",
            category="missing_fact",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32006,
        )

    # 6. Network & Connection Errors
    if "ConnectionError" in exc_type or "timeout" in exc_str.lower() or "ECONNREFUSED" in exc_str:
        return HumanizedError(
            user_message="Unable to connect to the job board or network service.",
            action_hint="Please check your internet connection and try again.",
            category="network_error",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32007,
        )

    # 7. Validation & Missing Fields
    if isinstance(exc, ValueError):
        return HumanizedError(
            user_message=f"Please check your input: {exc_str}",
            action_hint="Ensure all required fields are filled out correctly.",
            category="validation_error",
            technical_details=f"{exc_type}: {exc_str}",
            code=-32602,
        )

    # 8. Generic Fallback
    return HumanizedError(
        user_message="Something unexpected happened while processing your request.",
        action_hint="Try again in a few moments or run the Diagnostics check in Settings.",
        category="internal_error",
        technical_details=f"{exc_type}: {exc_str}",
        code=-32603,
    )
