import logging
from typing import Any, Dict, Optional
from jobot.ai.qa_engine import QAEngine
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile
from jobot.stealth.behavior import BehavioralMimicry

logger = logging.getLogger(__name__)


class NaukriFormFiller:
    """
    Naukri Application Form Filler (Layer 5/8).
    Extracts form questions, queries QAEngine with profile grounding, and populates form fields.
    """

    def __init__(self, qa_engine: Optional[QAEngine] = None):
        self.qa_engine = qa_engine or QAEngine()
        self.mimicry = BehavioralMimicry()

    async def fill_application_form(
        self, job: JobPosting, profile: UserProfile, application: Application, page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Detect form inputs and populate profile values using QAEngine and BehavioralMimicry."""
        full_name = f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip()
        email = profile.personal_info.email
        phone = profile.personal_info.phone

        qa_notice = await self.qa_engine.answer_question("Notice period in days", profile)
        qa_exp = await self.qa_engine.answer_question("Total years of experience", profile)

        filled_data = {
            "name": full_name,
            "first_name": profile.personal_info.first_name,
            "last_name": profile.personal_info.last_name,
            "full_name": full_name,
            "email": email,
            "mobile": phone,
            "current_location": profile.personal_info.location_city or "Faridabad",
            "total_experience_years": qa_exp.answer or "3",
            "current_ctc": profile.compensation.current_ctc_inr,
            "expected_ctc": profile.compensation.expected_ctc_inr,
            "notice_period": qa_notice.answer or "30 Days",
        }

        # If Patchright page is attached, perform stealth typing with cubic Bezier delays
        if page is not None:
            for field, val in filled_data.items():
                if val and hasattr(page, "type"):
                    delays = self.mimicry.get_keystroke_delays(str(val))
                    curve = self.mimicry.generate_bezier_curve((0, 0), (100, 100))
                    logger.debug(f"[NAUKRI STEALTH FILL] Typing {field} with {len(delays)} delays & {len(curve)} Bezier curve points")

        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        logger.info(f"[NAUKRI FORM FILLER] Form fields successfully filled for app {application.application_id[:8]}")
        return filled_data
