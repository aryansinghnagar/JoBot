from pathlib import Path
import pytest
from jobot.evals.harness import EvalCategory, EvalHarness, EvalScenario


def test_eval_harness_scenarios_from_dir():
    harness = EvalHarness()
    res = harness.run_eval_suite()

    assert res["total"] >= 5
    assert res["passed"] == res["total"]
    assert res["pass_rate"] == 1.0
    assert "regression" in res["category_scores"]
    assert "adversarial" in res["category_scores"]
    assert "capability" in res["category_scores"]
    assert "behavioral" in res["category_scores"]
    assert "long_horizon" in res["category_scores"]
