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


def test_eval_harness_detects_scenario_failure():
    harness = EvalHarness(scenarios_dir=Path("/nonexistent"))
    # Load a failing scenario: email mismatch expected to pass grounding check
    failing_scenario = EvalScenario(
        scenario_id="fail_test",
        category=EvalCategory.REGRESSION,
        title="Mismatch Failure Test",
        input_data={"filled_email": "wrong@example.com", "profile_email": "correct@example.com"},
        expected_output={"should_pass_grounding": True},
    )
    harness.load_scenario(failing_scenario)
    res = harness.run_eval_suite()

    assert res["total"] == 1
    assert res["passed"] == 0
    assert res["pass_rate"] == 0.0
