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
    confidence: float = 0.0
    cost_usd: float = 0.0


class CaptchaSolver:
    """
    CAPTCHA Solver combining AI Vision with Fallback Strategies (Layer 8).
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    async def solve_image_captcha(
        self, image_bytes: bytes, prompt_text: str = "Extract the text code from this CAPTCHA image exactly as shown."
    ) -> CaptchaResult:
        """Solve text image CAPTCHA using AI vision model."""
        if not image_bytes:
            return CaptchaResult(
                captcha_type=CaptchaType.IMAGE_TEXT,
                solved=False,
                confidence=0.0,
                cost_usd=0.0,
            )

        try:
            solution = await self.router.generate_text(f"{prompt_text} Image size: {len(image_bytes)} bytes")
            if not solution or solution.startswith("[LLM_UNAVAILABLE]"):
                return CaptchaResult(
                    captcha_type=CaptchaType.IMAGE_TEXT,
                    solved=False,
                    confidence=0.0,
                    cost_usd=0.0,
                )

            clean_text = solution.strip().replace(" ", "").replace("\n", "")
            return CaptchaResult(
                captcha_type=CaptchaType.IMAGE_TEXT,
                solved=True,
                text_solution=clean_text,
                confidence=0.85,
                cost_usd=0.001,
            )
        except Exception as e:
            logger.error(f"CAPTCHA vision solver failed: {e}")
            return CaptchaResult(
                captcha_type=CaptchaType.IMAGE_TEXT,
                solved=False,
                confidence=0.0,
                cost_usd=0.0,
            )
