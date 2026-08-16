"""Backward-compatible re-export shim.

ModelRouter v2 lives in `jobot.llm.router` (plan.md Chapter 6). This module
keeps the frozen `jobot.ai.router.ModelRouter.generate_text` import path
working for QAEngine, SkillExtractor, and existing tests.
"""

from jobot.llm.router import ModelCallMetrics, ModelProvider, ModelRouter

__all__ = ["ModelCallMetrics", "ModelProvider", "ModelRouter"]
