import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from jobot.ai.router import ModelRouter

logger = logging.getLogger(__name__)


class CaptchaType(str, Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE_TURNSTILE = "cloudflare_turnstile"
    IMAGE_TEXT = "image_text"


class CaptchaResult(BaseModel):
    captcha_type: CaptchaType
    solved: bool
    token: Optional[str] = None
    text_solution: Optional[str] = None
    cost_usd: float = 0.0


class CaptchaSolver:
    """
    CAPTCHA Solver combining AI Vision (Gemini) with Paid Solving Services.
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    async def solve_image_captcha(self, image_bytes: bytes) -> CaptchaResult:
        """Solve text image CAPTCHA using Gemini AI vision model."""
        prompt = "Extract the text code from this CAPTCHA image exactly as shown."
        try:
            solution = await self.router.generate_text(prompt)
            clean_text = solution.strip().replace(" ", "")
            return CaptchaResult(
                captcha_type=CaptchaType.IMAGE_TEXT,
                solved=True,
                text_solution=clean_text,
                cost_usd=0.001,
            )
        except Exception as e:
            logger.error(f"CAPTCHA vision solver failed: {e}")
            return CaptchaResult(
                captcha_type=CaptchaType.IMAGE_TEXT,
                solved=False,
                cost_usd=0.0,
            )
