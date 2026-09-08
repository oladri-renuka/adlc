"""Tests for Component 2: Deterministic Guardrail Engine."""

import pytest
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrail_engine import GuardrailEngine, GuardrailViolation, GuardrailType
from skill_parser import load_skills
from database_models import DatabaseManager


@pytest.fixture
def temp_db():
    """Create temporary database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield f"sqlite:///{db_path}"
    # Cleanup happens automatically


@pytest.fixture
def skill_registry():
    """Load skill registry."""
    return load_skills("skills")


@pytest.fixture
def db_manager(temp_db):
    """Create database manager with temp database."""
    return DatabaseManager(temp_db)


@pytest.fixture
def guardrail_engine(skill_registry, db_manager):
    """Create guardrail engine instance."""
    return GuardrailEngine(skill_registry, db_manager)


class TestGuardrailForbiddenPhrases:
    """Test forbidden phrase guardrails."""

    def test_forbidden_phrase_detected(self, guardrail_engine):
        """Detect forbidden phrase in response."""
        response = "I guarantee this will solve your problem."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None
        assert violation.guardrail_name == "forbidden_phrases"
        assert "I guarantee" in violation.violation_description

    def test_forbidden_phrase_case_insensitive(self, guardrail_engine):
        """Forbidden phrase check is case-insensitive."""
        response = "I GUARANTEE this will work."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_multiple_forbidden_phrases(self, guardrail_engine):
        """Detect when response contains multiple forbidden phrases."""
        response = "I promise to give you our competitor's prices."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_no_forbidden_phrase_passes(self, guardrail_engine):
        """Response without forbidden phrases passes."""
        response = "We'd like to offer you a special discount to keep you as a valued customer."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert is_valid
        assert violation is None


class TestGuardrailDiscountBounds:
    """Test numeric discount bound guardrails."""

    def test_discount_exceeds_max(self, guardrail_engine):
        """Detect when discount exceeds maximum."""
        response = "We can offer you a 50% discount on your plan."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None
        assert violation.guardrail_name == "max_discount_percent"
        assert "50" in violation.violation_description

    def test_discount_at_max_passes(self, guardrail_engine):
        """Discount at exactly max value passes."""
        response = "We can offer you a 30% discount, which is our maximum discount."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert is_valid
        assert violation is None

    def test_discount_below_max_passes(self, guardrail_engine):
        """Discount below max value passes."""
        response = "We're able to offer you a 15% discount on your plan."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert is_valid
        assert violation is None

    def test_discount_decimal_values(self, guardrail_engine):
        """Detect decimal discount values that exceed max."""
        response = "We can provide a 35.5% discount."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None


class TestGuardrailEscalationRequired:
    """Test mandatory escalation guardrails."""

    def test_disability_accommodation_triggers_escalation(self, guardrail_engine):
        """Disability accommodation mention triggers escalation."""
        response = "Thank you for mentioning your disability accommodation needs. We'll escalate this to our accessibility team."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None
        assert "escalation" in violation.guardrail_name.lower()

    def test_legal_mention_triggers_escalation(self, guardrail_engine):
        """Legal action mention triggers escalation."""
        response = "I understand you mentioned legal action. This requires immediate escalation to our legal team."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_regulatory_complaint_triggers_escalation(self, guardrail_engine):
        """Regulatory complaint mention triggers escalation."""
        response = "Since you mentioned a regulatory complaint, we're immediately escalating this to our compliance team."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_normal_technical_issue_passes(self, guardrail_engine):
        """Normal technical issue without escalation triggers passes."""
        response = "Let me help you troubleshoot your connectivity issue. Have you tried restarting your router?"
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert is_valid
        assert violation is None


class TestGuardrailFalsePromises:
    """Test false promise detection guardrails."""

    def test_guarantee_detected(self, guardrail_engine):
        """False promise 'guarantee' detected."""
        response = "I guarantee your service will be restored by tomorrow."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None
        assert "false promise" in violation.guardrail_name.lower() or "guarantee" in violation.violation_description.lower()

    def test_definitely_will_detected(self, guardrail_engine):
        """False promise 'definitely will' detected."""
        response = "Your connection will definitely be fixed within 2 hours."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_100_percent_sure_detected(self, guardrail_engine):
        """False promise '100% sure' detected."""
        response = "I'm 100% sure this will resolve your problem."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None

    def test_appropriate_language_passes(self, guardrail_engine):
        """Appropriate language without false promises passes."""
        response = "We'll do our best to resolve this quickly. Let me create a support ticket for you."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert is_valid
        assert violation is None


class TestGuardrailEnforcement:
    """Test the enforce() method with regeneration."""

    def test_enforce_returns_valid_on_pass(self, guardrail_engine):
        """Enforce returns original response when no violations."""
        response = "We can offer you a 20% discount to keep your business."
        success, final_response, violation = guardrail_engine.enforce(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert success
        assert final_response == response
        assert violation is None

    def test_enforce_detects_violation(self, guardrail_engine):
        """Enforce detects and returns violation."""
        response = "I guarantee we can offer you 50% off."
        success, final_response, violation = guardrail_engine.enforce(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not success
        assert violation is not None

    def test_enforce_attempts_regeneration(self, guardrail_engine):
        """Enforce attempts to regenerate violating responses."""
        response = "I promise to give you 40% discount!"
        success, final_response, violation = guardrail_engine.enforce(
            "retention_offer",
            response,
            "conv_123",
            1,
            prompt="Generate a retention offer",
        )

        # Violation should be detected
        assert violation is not None
        # Regenerated response should have constraint appended
        if final_response:
            assert "[CONSTRAINT" in final_response or final_response == ""


class TestGuardrailLogging:
    """Test violation logging to database."""

    def test_violation_logged_to_database(self, guardrail_engine, db_manager):
        """Violations are logged to database."""
        response = "I guarantee 50% discount."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid

        # Check database has the violation
        violations = db_manager.get_violations_for_conversation("conv_123")
        assert len(violations) > 0

    def test_violation_contains_all_fields(self, guardrail_engine, db_manager):
        """Logged violation contains all required fields."""
        response = "I promise to offer you 45% discount."
        guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        violations = db_manager.get_violations_for_conversation("conv_123")
        assert len(violations) > 0

        violation = violations[0]
        assert violation.conversation_id == "conv_123"
        assert violation.turn_number == 1
        assert violation.skill_id == "retention_offer"
        assert violation.guardrail_name is not None
        assert violation.guardrail_type is not None
        assert violation.original_response == response
        assert violation.timestamp is not None


class TestGuardrailStats:
    """Test violation statistics tracking."""

    def test_violation_stats_empty_initially(self, guardrail_engine):
        """Violation stats empty when no violations."""
        stats = guardrail_engine.get_violation_stats()
        assert stats == {}

    def test_violation_stats_tracks_violations(self, guardrail_engine):
        """Violation stats track violation counts."""
        # First violation
        guardrail_engine.check_response(
            "retention_offer",
            "I guarantee 50% off",
            "conv_123",
            1,
        )

        # Second violation
        guardrail_engine.check_response(
            "retention_offer",
            "I promise 40% discount",
            "conv_123",
            2,
        )

        stats = guardrail_engine.get_violation_stats()
        assert "forbidden_phrases" in stats or "max_discount_percent" in stats

    def test_get_violations_returns_all(self, guardrail_engine):
        """get_violations returns all logged violations."""
        guardrail_engine.check_response(
            "retention_offer",
            "I guarantee 50% off",
            "conv_123",
            1,
        )

        guardrail_engine.check_response(
            "retention_offer",
            "I promise 45% discount",
            "conv_123",
            2,
        )

        violations = guardrail_engine.get_violations()
        assert len(violations) == 2

    def test_clear_log_empties_violations(self, guardrail_engine):
        """clear_log empties violation log."""
        guardrail_engine.check_response(
            "retention_offer",
            "I guarantee 50% off",
            "conv_123",
            1,
        )

        guardrail_engine.clear_log()
        violations = guardrail_engine.get_violations()
        assert len(violations) == 0


class TestGuardrailMultipleViolations:
    """Test handling of multiple violations in single response."""

    def test_detects_first_violation(self, guardrail_engine):
        """Detects first violation when multiple exist."""
        response = "I guarantee to offer you 50% discount on your service."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None
        # Should catch one of the violations
        assert violation.guardrail_name in [
            "forbidden_phrases",
            "max_discount_percent",
        ]

    def test_response_with_high_discount_and_promise(self, guardrail_engine):
        """Response with both high discount and false promise."""
        response = "I definitely guarantee we can offer 60% discount."
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid
        assert violation is not None


class TestGuardrailDifferentSkills:
    """Test guardrails work across different skills."""

    def test_retention_offer_guardrails(self, guardrail_engine):
        """Retention offer has applicable guardrails."""
        response = "50% discount guaranteed!"
        is_valid, violation = guardrail_engine.check_response(
            "retention_offer",
            response,
            "conv_123",
            1,
        )

        assert not is_valid

    def test_technical_escalation_guardrails(self, guardrail_engine):
        """Technical escalation has applicable guardrails."""
        response = "Your service will definitely be restored in 1 hour, I guarantee it."
        is_valid, violation = guardrail_engine.check_response(
            "technical_escalation",
            response,
            "conv_123",
            1,
        )

        assert not is_valid

    def test_account_lookup_passes_safely(self, guardrail_engine):
        """Account lookup can pass safely without guardrail issues."""
        response = "Your account details: Plan: Premium, Balance: $0, Usage: 75% of limit."
        is_valid, violation = guardrail_engine.check_response(
            "account_lookup",
            response,
            "conv_123",
            1,
        )

        # Should pass (no guardrails defined for account_lookup in terms of
        # forbidden phrases/discounts)
        assert is_valid or violation is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
