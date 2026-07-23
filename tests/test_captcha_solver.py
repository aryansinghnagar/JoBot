import pytest
from jobot.stealth.captcha import CaptchaResult, CaptchaSolver, CaptchaType


@pytest.mark.asyncio
async def test_captcha_solver_empty_bytes():
    solver = CaptchaSolver()
    res = await solver.solve_image_captcha(b"")

    assert res.solved is False
    assert res.confidence == 0.0


@pytest.mark.asyncio
async def test_captcha_solver_image_bytes():
    solver = CaptchaSolver()
    sample_bytes = b"GIF89a_fake_captcha_image_data"
    res = await solver.solve_image_captcha(sample_bytes)

    assert isinstance(res, CaptchaResult)
    assert res.captcha_type == CaptchaType.IMAGE_TEXT
