import pytest
from jobot.evals.harness import EvalCategory, EvalHarness, EvalScenario


def test_eval_harness_execution():
    harness = EvalHarness()
    scenario = EvalScenario(
        scenario_id="eval_001",
        category=EvalCategory.CAPABILITY,
        title="Form Fill Capability Test",
        input_data={"job_url": "https://naukri.com/job/101"},
        expected_output={"status": "verified"},
    )
    harness.load_scenario(scenario)

    results = harness.run_eval_suite()
    assert results["total"] == 1
    assert results["passed"] == 1
    assert results["pass_rate"] == 1.0
    assert "capability" in results["category_scores"]
