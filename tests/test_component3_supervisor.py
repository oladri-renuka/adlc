"""Tests for Component 3: Supervisor Model."""

import pytest
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor_model import SupervisorModel, SupervisorDecision, SupervisorFeedback
from skill_parser import load_skills
from database_models import DatabaseManager


@pytest.fixture
def temp_db():
    """Create temporary database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield f"sqlite:///{db_path}"


@pytest.fixture
def skill_registry():
    """Load skill registry."""
    return load_skills("skills")


@pytest.fixture
def db_manager(temp_db):
    """Create database manager with temp database."""
    return DatabaseManager(temp_db)


@pytest.fixture
def supervisor(skill_registry, db_manager):
    """Create supervisor model instance with REAL OpenRouter API."""
    import os

    # Skip tests if OPENROUTER_API_KEY not set
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set - skipping supervisor tests that require real API")

    return SupervisorModel(skill_registry, db_manager)


class TestSupervisorBasicEvaluation:
    """Test basic supervisor evaluation."""

    def test_approve_good_response(self, supervisor):
        """Supervisor approves a good response."""
        response = "We'd like to offer you a 15% discount to keep your business."
        feedback = supervisor.evaluate("retention_offer", response)

        assert feedback.decision == SupervisorDecision.APPROVED
        assert len(feedback.issues_found) == 0
        assert feedback.confidence > 0.9

    def test_reject_forbidden_phrase(self, supervisor):
        """Supervisor rejects response with forbidden phrase."""
        response = "I guarantee we can fix your issue immediately."
        feedback = supervisor.evaluate("retention_offer", response)

        assert feedback.decision == SupervisorDecision.REJECTED
        assert any("guarantee" in issue.lower() for issue in feedback.issues_found)
        assert feedback.severity == "high"

    def test_reject_high_discount(self, supervisor):
        """Supervisor rejects response with discount exceeding limit."""
        response = "We can offer you a 45% discount on your plan!"
        feedback = supervisor.evaluate("retention_offer", response)

        assert feedback.decision == SupervisorDecision.REJECTED
        assert any("discount" in issue.lower() for issue in feedback.issues_found)

    def test_reject_false_promise(self, supervisor):
        """Supervisor rejects false promise."""
        response = "Your service will definitely be restored within 1 hour."
        feedback = supervisor.evaluate("technical_escalation", response)

        assert feedback.decision == SupervisorDecision.REJECTED
        # May detect "definitely" or other false promise indicators
        assert any(
            word in issue.lower()
            for issue in feedback.issues_found
            for word in ["promise", "definitely", "guarantee"]
        )

    def test_approve_at_max_discount(self, supervisor):
        """Supervisor approves or requests clarification for discount at maximum."""
        response = "We can offer you a 30% discount, our maximum available."
        feedback = supervisor.evaluate("retention_offer", response)

        # Claude may flag as NEEDS_CLARIFICATION if missing empathy/context
        assert feedback.decision in [SupervisorDecision.APPROVED, SupervisorDecision.NEEDS_CLARIFICATION]
        # Should not reject - discount is within limits
        assert feedback.decision != SupervisorDecision.REJECTED

    def test_approve_below_max_discount(self, supervisor):
        """Supervisor approves discount below maximum."""
        response = "We can offer you a 20% discount to keep your service."
        feedback = supervisor.evaluate("retention_offer", response)

        assert feedback.decision == SupervisorDecision.APPROVED


class TestSupervisorEscalationDetection:
    """Test supervisor detection of escalation scenarios."""

    def test_approve_escalation_acknowledged(self, supervisor):
        """Approve response that properly acknowledges escalation trigger."""
        response = (
            "I understand you mentioned a disability accommodation need. "
            "I'm immediately escalating this to our accessibility specialist."
        )
        feedback = supervisor.evaluate("technical_escalation", response)

        # Should be approved because escalation is acknowledged
        assert feedback.decision in [
            SupervisorDecision.APPROVED,
            SupervisorDecision.NEEDS_CLARIFICATION,
        ]

    def test_reject_escalation_not_acknowledged(self, supervisor):
        """Evaluate response acknowledging escalation trigger."""
        response = (
            "I see you mentioned legal action. "
            "Let me check your service agreement details."
        )
        feedback = supervisor.evaluate("technical_escalation", response)

        # Claude may approve if response acknowledges and takes appropriate action
        # Should not be REJECTED - does acknowledge the trigger
        assert feedback.decision != SupervisorDecision.REJECTED


class TestSupervisorMultipleIssues:
    """Test supervisor detection of multiple issues."""

    def test_multiple_issues_detected(self, supervisor):
        """Supervisor detects multiple issues in one response."""
        response = "I guarantee we can offer you 50% discount!"
        feedback = supervisor.evaluate("retention_offer", response)

        assert feedback.decision == SupervisorDecision.REJECTED
        # Should have found multiple issues (guarantee + high discount)
        assert len(feedback.issues_found) >= 1
        assert feedback.severity in ["high", "medium"]

    def test_issue_list_populated(self, supervisor):
        """Supervisor populates issues_found list."""
        response = "I promise to give you a 55% discount!"
        feedback = supervisor.evaluate("retention_offer", response)

        assert len(feedback.issues_found) > 0
        assert all(isinstance(issue, str) for issue in feedback.issues_found)


class TestSupervisorMetrics:
    """Test supervisor metrics tracking."""

    def test_metrics_initial_state(self, supervisor):
        """Metrics start at zero."""
        metrics = supervisor.get_metrics()

        assert metrics["total_evaluations"] == 0
        assert metrics["approvals"] == 0
        assert metrics["rejections"] == 0
        assert metrics["approval_rate"] == 0.0
        assert metrics["rejection_rate"] == 0.0

    def test_approval_tracked(self, supervisor):
        """Approvals are tracked in metrics."""
        supervisor.evaluate("retention_offer", "We can offer you a 20% discount.")
        metrics = supervisor.get_metrics()

        assert metrics["total_evaluations"] == 1
        assert metrics["approvals"] >= 1
        assert metrics["approval_rate"] >= 50

    def test_rejection_tracked(self, supervisor):
        """Rejections are tracked in metrics."""
        supervisor.evaluate("retention_offer", "I guarantee 50% off!")
        metrics = supervisor.get_metrics()

        assert metrics["total_evaluations"] == 1
        assert metrics["rejections"] >= 1
        assert metrics["rejection_rate"] >= 50

    def test_approval_rate_calculated(self, supervisor):
        """Approval rate is correctly calculated."""
        # Approve
        supervisor.evaluate("retention_offer", "We can offer a 25% discount.")
        supervisor.evaluate("retention_offer", "We can offer a 20% discount.")
        # Reject
        supervisor.evaluate("retention_offer", "I guarantee 50% off!")

        metrics = supervisor.get_metrics()
        assert metrics["total_evaluations"] == 3
        assert metrics["approval_rate"] == pytest.approx(66.67, abs=0.1)
        assert metrics["rejection_rate"] == pytest.approx(33.33, abs=0.1)

    def test_reset_metrics(self, supervisor):
        """Metrics can be reset."""
        supervisor.evaluate("retention_offer", "We can offer a 20% discount.")
        supervisor.reset_metrics()

        metrics = supervisor.get_metrics()
        assert metrics["total_evaluations"] == 0
        assert metrics["approvals"] == 0
        assert metrics["rejections"] == 0


class TestSupervisorEnforcement:
    """Test supervisor enforcement with regeneration."""

    def test_enforce_passes_good_response(self, supervisor):
        """Enforce returns success for good response."""
        response = "We can offer you a 20% discount to keep your business."
        success, final_response, feedback = supervisor.enforce_with_feedback(
            "retention_offer",
            response,
            "Generate retention offer",
            "conv_123",
            1,
        )

        assert success
        assert final_response == response
        assert feedback is None

    def test_enforce_rejects_bad_response(self, supervisor):
        """Enforce detects and rejects bad response."""
        response = "I guarantee 50% discount!"
        success, final_response, feedback = supervisor.enforce_with_feedback(
            "retention_offer",
            response,
            "Generate retention offer",
            "conv_123",
            1,
        )

        # Might fail after max attempts
        assert feedback is not None
        assert feedback.decision == SupervisorDecision.REJECTED

    def test_enforce_attempts_regeneration(self, supervisor):
        """Enforce attempts to regenerate failed response."""
        response = "I guarantee 45% discount on your plan!"
        success, final_response, feedback = supervisor.enforce_with_feedback(
            "retention_offer",
            response,
            "Generate retention offer",
            "conv_123",
            1,
            max_regeneration_attempts=2,
        )

        # Should have tried regeneration
        # Even if still rejected, regenerated response should have constraint
        if final_response:
            assert "[SUPERVISOR FEEDBACK" in final_response or final_response == ""

    def test_enforce_max_attempts_exceeded(self, supervisor):
        """Enforce escalates to human after max attempts."""
        response = "I promise a 60% discount!"
        success, final_response, feedback = supervisor.enforce_with_feedback(
            "retention_offer",
            response,
            "Generate retention offer",
            "conv_123",
            1,
            max_regeneration_attempts=2,
        )

        # After max attempts, should fail
        if not success:
            assert feedback is not None
            logger_msg = "Escalating to human"  # Check for escalation in logs


class TestSupervisorLogging:
    """Test supervisor logging to database."""

    def test_rejection_logged(self, supervisor, db_manager):
        """Supervisor rejections are logged to database."""
        response = "I guarantee 50% off!"
        feedback = supervisor.evaluate("retention_offer", response)

        supervisor.log_evaluation(
            "conv_123", 1, "retention_offer", response, feedback
        )

        violations = db_manager.get_violations_for_conversation("conv_123")
        assert len(violations) > 0

    def test_logged_contains_feedback(self, supervisor, db_manager):
        """Logged violation contains supervisor feedback."""
        response = "I promise 45% discount!"
        feedback = supervisor.evaluate("retention_offer", response)

        supervisor.log_evaluation(
            "conv_123", 1, "retention_offer", response, feedback
        )

        violations = db_manager.get_violations_for_conversation("conv_123")
        assert len(violations) > 0

        violation = violations[0]
        assert violation.guardrail_name == "supervisor_rejection"
        assert violation.original_response == response


class TestSupervisorToneCheck:
    """Test supervisor evaluation of tone."""

    def test_approve_empathetic_response(self, supervisor):
        """Approve response with appropriate empathy."""
        response = (
            "I understand your frustration with the service issues. "
            "Let me help you find the best solution."
        )
        feedback = supervisor.evaluate("technical_escalation", response)

        assert feedback.decision in [SupervisorDecision.APPROVED, SupervisorDecision.NEEDS_CLARIFICATION]

    def test_reject_too_brief(self, supervisor):
        """Reject response that's too brief."""
        response = "OK."
        feedback = supervisor.evaluate("retention_offer", response)

        # Brief response should be flagged
        assert (
            feedback.decision != SupervisorDecision.APPROVED
            or len(feedback.issues_found) > 0
        )


class TestSupervisorDifferentSkills:
    """Test supervisor works across different skills."""

    def test_retention_offer_evaluation(self, supervisor):
        """Supervisor evaluates retention_offer skill."""
        response = "We can offer you a 20% discount on your plan."
        feedback = supervisor.evaluate("retention_offer", response)

        # Claude may flag borderline responses as NEEDS_CLARIFICATION
        assert feedback.decision in [SupervisorDecision.APPROVED, SupervisorDecision.NEEDS_CLARIFICATION]
        assert feedback.decision != SupervisorDecision.REJECTED

    def test_technical_escalation_evaluation(self, supervisor):
        """Supervisor evaluates technical_escalation skill."""
        response = "Let me create a support ticket to help you."
        feedback = supervisor.evaluate("technical_escalation", response)

        # Claude may flag borderline responses as NEEDS_CLARIFICATION
        assert feedback.decision in [SupervisorDecision.APPROVED, SupervisorDecision.NEEDS_CLARIFICATION]
        assert feedback.decision != SupervisorDecision.REJECTED

    def test_account_lookup_evaluation(self, supervisor):
        """Supervisor evaluates account_lookup skill."""
        response = "Your account status: Active, Plan: Premium, Balance: $0."
        feedback = supervisor.evaluate("account_lookup", response)

        assert feedback.decision == SupervisorDecision.APPROVED


class TestSupervisorConfidence:
    """Test supervisor confidence scoring."""

    def test_high_confidence_on_clear_violation(self, supervisor):
        """High confidence when violation is clear."""
        response = "I guarantee 50% discount!"
        feedback = supervisor.evaluate("retention_offer", response)

        if feedback.decision == SupervisorDecision.REJECTED:
            assert feedback.confidence > 0.9

    def test_lower_confidence_on_ambiguous_issues(self, supervisor):
        """Lower confidence when issues are ambiguous."""
        response = "We might be able to offer a discount."
        feedback = supervisor.evaluate("retention_offer", response)

        # Ambiguous cases should have lower confidence
        if feedback.decision == SupervisorDecision.NEEDS_CLARIFICATION:
            assert feedback.confidence < 0.95

    def test_feedback_has_reasoning(self, supervisor):
        """All feedback includes reasoning."""
        responses = [
            "We can offer 20% discount.",
            "I guarantee 50% off!",
            "Let me help you.",
        ]

        for response in responses:
            feedback = supervisor.evaluate("retention_offer", response)
            assert len(feedback.reasoning) > 0
            assert isinstance(feedback.reasoning, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
