"""Regression Test Suite Runner - Tests agent against scripted conversations."""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_parser import load_skills
from guardrail_engine import GuardrailEngine
from supervisor_model import SupervisorModel
from database_models import DatabaseManager


class RegressionTestRunner:
    """Run scripted conversation tests against the agent."""

    def __init__(self, db_path: str = "regression_tests.db"):
        """Initialize test runner with loaded components."""
        self.skill_registry = load_skills("skills")
        self.db_manager = DatabaseManager(f"sqlite:///{db_path}")
        self.guardrail_engine = GuardrailEngine(self.skill_registry, self.db_manager)

        # Supervisor requires API key but is optional for basic tests
        try:
            import os
            if os.getenv("OPENROUTER_API_KEY"):
                self.supervisor = SupervisorModel(self.skill_registry, self.db_manager)
            else:
                self.supervisor = None
        except ValueError:
            self.supervisor = None

        self.test_results = []
        self.metrics = {
            "total_conversations": 0,
            "passed": 0,
            "failed": 0,
            "violations_found": 0,
            "violations_caught": 0,
            "guardrail_stats": {},
        }

    def run_test(self, test_file: Path) -> Dict[str, Any]:
        """Run a single conversation test."""
        with open(test_file, "r") as f:
            test_data = json.load(f)

        scenario_id = test_data.get("scenario_id", "unknown")
        test_name = test_data.get("name", scenario_id)
        skill_id = test_data.get("skill_id", "retention_offer")
        variations = test_data.get("variations", [])

        test_result = {
            "test_file": str(test_file.name),
            "scenario_id": scenario_id,
            "name": test_name,
            "skill_id": skill_id,
            "total_variations": len(variations),
            "passed_variations": 0,
            "failed_variations": 0,
            "details": [],
        }

        for var_idx, variation in enumerate(variations):
            var_result = self._run_variation(scenario_id, var_idx, variation, skill_id)
            test_result["details"].append(var_result)

            if var_result["passed"]:
                test_result["passed_variations"] += 1
            else:
                test_result["failed_variations"] += 1

        # Test passes if all variations pass
        passed = test_result["failed_variations"] == 0
        test_result["passed"] = passed

        if passed:
            self.metrics["passed"] += 1
        else:
            self.metrics["failed"] += 1

        self.metrics["total_conversations"] += 1
        self.test_results.append(test_result)

        return test_result

    def _run_variation(self, scenario_id: str, var_idx: int, variation: Dict, skill_id: str = "retention_offer") -> Dict[str, Any]:
        """Run a single conversation variation."""
        turns = variation.get("turns", [])
        expected_violations = variation.get("expected_violations", [])

        var_result = {
            "variation": var_idx,
            "turns": len(turns),
            "expected_violations": expected_violations,
            "detected_violations": [],
            "supervisor_decisions": [],
            "passed": True,
            "issues": [],
        }

        conversation_id = f"{scenario_id}_var_{var_idx}"

        for turn_idx, turn in enumerate(turns):
            agent_response = turn.get("agent_response", "")

            # Check guardrails
            is_valid, violation = self.guardrail_engine.check_response(
                skill_id,
                agent_response,
                conversation_id,
                turn_idx,
            )

            if not is_valid:
                var_result["detected_violations"].append(
                    {
                        "turn": turn_idx,
                        "type": violation.guardrail_name if violation else "unknown",
                        "description": violation.violation_description if violation else "",
                    }
                )

                # Update metrics
                self.metrics["violations_found"] += 1
                guardrail_name = violation.guardrail_name if violation else "unknown"
                if guardrail_name not in self.metrics["guardrail_stats"]:
                    self.metrics["guardrail_stats"][guardrail_name] = {
                        "violations": 0,
                        "caught": 0,
                    }
                self.metrics["guardrail_stats"][guardrail_name]["violations"] += 1

                # Check if this violation was expected
                if guardrail_name in expected_violations:
                    self.metrics["guardrail_stats"][guardrail_name]["caught"] += 1
                    self.metrics["violations_caught"] += 1

            # Optionally check supervisor (if API key available)
            if self.supervisor:
                feedback = self.supervisor.evaluate(skill_id, agent_response)
                var_result["supervisor_decisions"].append(
                    {
                        "turn": turn_idx,
                        "decision": feedback.decision.value,
                        "confidence": feedback.confidence,
                    }
                )

        # Check if expected violations were detected
        detected_types = {v["type"] for v in var_result["detected_violations"]}
        for expected in expected_violations:
            if expected not in detected_types:
                var_result["issues"].append(
                    f"Expected violation '{expected}' not detected"
                )
                var_result["passed"] = False

        return var_result

    def run_all_tests(self, test_dir: str = "tests/conversations") -> Dict[str, Any]:
        """Run all conversation tests."""
        test_path = Path(test_dir)
        if not test_path.exists():
            print(f"❌ Test directory not found: {test_dir}")
            return {"error": f"Directory {test_dir} does not exist"}

        json_files = sorted(test_path.glob("*.json"))
        if not json_files:
            print(f"❌ No test files found in {test_dir}")
            return {"error": "No JSON test files found"}

        print(f"\n{'='*80}")
        print(f"REGRESSION TEST SUITE RUNNER")
        print(f"{'='*80}\n")
        print(f"Running {len(json_files)} conversation tests...\n")

        for idx, test_file in enumerate(json_files, 1):
            result = self.run_test(test_file)
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(
                f"[{idx:3d}/{len(json_files)}] {status} - {result['name']} "
                f"({result['passed_variations']}/{result['total_variations']} variations)"
            )

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate final test report."""
        total = self.metrics["total_conversations"]
        passed = self.metrics["passed"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": self.metrics["failed"],
                "pass_rate": round(pass_rate, 2),
            },
            "violations": {
                "total_found": self.metrics["violations_found"],
                "caught_by_guardrails": self.metrics["violations_caught"],
                "detection_rate": (
                    round(
                        self.metrics["violations_caught"]
                        / self.metrics["violations_found"]
                        * 100,
                        2,
                    )
                    if self.metrics["violations_found"] > 0
                    else 0
                ),
                "by_type": self.metrics["guardrail_stats"],
            },
            "test_results": self.test_results,
        }

        return report

    def save_report(self, output_file: str = "regression_report.json"):
        """Save test report to JSON file."""
        report = self._generate_report()

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'='*80}")
        print(f"REPORT SAVED: {output_file}")
        print(f"{'='*80}\n")

        # Print summary
        summary = report["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']}%\n")

        violations = report["violations"]
        print(f"Guardrail Violations Found: {violations['total_found']}")
        print(f"Violations Caught: {violations['caught_by_guardrails']}")
        print(f"Detection Rate: {violations['detection_rate']}%\n")

        return output_file


def main():
    """Run regression test suite."""
    runner = RegressionTestRunner()
    report = runner.run_all_tests()
    runner.save_report("tests/regression_report.json")

    # Print summary
    if "error" not in report:
        summary = report["summary"]
        if summary["pass_rate"] == 100:
            print("✅ All tests passed!")
        else:
            print(f"⚠️  {summary['failed']} test(s) failed")


if __name__ == "__main__":
    main()
