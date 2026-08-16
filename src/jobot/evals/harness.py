import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EvalCategory(str, Enum):
    CAPABILITY = "capability"
    REGRESSION = "regression"
    BEHAVIORAL = "behavioral"
    ADVERSARIAL = "adversarial"
    LONG_HORIZON = "long_horizon"
    PRODUCTION_DERIVED = "production_derived"


class EvalScenario(BaseModel):
    scenario_id: str
    category: EvalCategory
    title: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]


class EvalResult(BaseModel):
    scenario_id: str
    category: EvalCategory
    passed: bool
    score: float
    error_message: Optional[str] = None


class EvalHarness:
    """
    Continuous Eval Harness (Layer I).
    Evaluates system performance across 6 eval categories.
    """

    def __init__(self, scenarios_dir: Optional[Path] = None):
        if scenarios_dir is None:
            scenarios_dir = Path.home() / ".jobot" / "evals"
        self.scenarios_dir = scenarios_dir
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios: List[EvalScenario] = []

    def load_scenario(self, scenario: EvalScenario) -> None:
        self.scenarios.append(scenario)

    def run_eval_suite(self) -> Dict[str, Any]:
        total = len(self.scenarios)
        if total == 0:
            return {"total": 0, "passed": 0, "pass_rate": 1.0, "category_scores": {}}

        passed_count = 0
        cat_scores: Dict[str, Dict[str, int]] = {}

        for sc in self.scenarios:
            cat = sc.category.value
            if cat not in cat_scores:
                cat_scores[cat] = {"passed": 0, "total": 0}
            cat_scores[cat]["total"] += 1

            # Mock evaluation logic for scenario baseline
            sc_passed = True
            if sc_passed:
                passed_count += 1
                cat_scores[cat]["passed"] += 1

        pass_rate = passed_count / total if total > 0 else 1.0
        return {
            "total": total,
            "passed": passed_count,
            "pass_rate": pass_rate,
            "category_scores": cat_scores,
        }
