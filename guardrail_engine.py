"""Deterministic Guardrail Engine - intercepts LLM output and enforces constraints."""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

from skill_models import Skill, SkillRegistry
from database_models import DatabaseManager, GuardrailViolationSchema

logger = logging.getLogger(__name__)


class GuardrailType(str, Enum):
    """Types of guardrails that can be enforced."""
    NUMERIC_BOUNDS = "numeric_bounds"
    FORBIDDEN_PHRASES = "forbidden_phrases"
    REQUIRED_CONFIRMATIONS = "required_confirmations"
    SCOPE_LIMITS = "scope_limits"
    ESCALATION_REQUIRED = "escalation_required"


class GuardrailViolation:
    """Represents a guardrail violation."""

    def __init__(
        self,
        guardrail_name: str,
        guardrail_type: GuardrailType,
        violation_description: str,
        original_response: str,
    ):
        self.guardrail_name = guardrail_name
        self.guardrail_type = guardrail_type
        self.violation_description = violation_description
        self.original_response = original_response


class GuardrailEngine:
    """
    Intercepts LLM output and enforces guardrails before reaching user.

    Behavior:
    1. Check LLM response against guardrails
    2. If violation found:
       a. Log violation to database
       b. Regenerate response with violation as negative constraint
       c. Retry up to 2 times
    3. If regeneration succeeds, continue; if all retries fail, escalate to human
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        db_manager: DatabaseManager,
        max_regeneration_attempts: int = 2,
    ):
        """Initialize guardrail engine with skill registry and database."""
        self.skill_registry = skill_registry
        self.db_manager = db_manager
        self.max_regeneration_attempts = max_regeneration_attempts
        self.violations_log: List[GuardrailViolation] = []

    def check_response(
        self,
        skill_id: str,
        response: str,
        conversation_id: str,
        turn_number: int,
    ) -> Tuple[bool, Optional[GuardrailViolation]]:
        """
        Check LLM response against guardrails for a skill.

        Returns:
            (is_valid, violation)
            - is_valid: True if no violations found
            - violation: GuardrailViolation object if violation found, else None
        """
        skill = self.skill_registry.get_skill(skill_id)
        if not skill:
            logger.error(f"Skill {skill_id} not found in registry")
            return False, None

        # Check each guardrail defined for the skill
        for guardrail_def in skill.guardrails:
            if isinstance(guardrail_def, dict):
                violation = self._check_guardrail(guardrail_def, response, skill_id)
                if violation:
                    # Log the violation
                    self._log_violation(
                        violation, skill_id, conversation_id, turn_number, response
                    )
                    return False, violation

        return True, None

    def _check_guardrail(
        self, guardrail_def: Dict, response: str, skill_id: str
    ) -> Optional[GuardrailViolation]:
        """Check a single guardrail definition against response."""

        # Check for forbidden phrases
        if "forbidden_phrases" in guardrail_def:
            phrases = guardrail_def["forbidden_phrases"]
            violation = self._check_forbidden_phrases(
                phrases, response, guardrail_def.get("action_on_violation")
            )
            if violation:
                return violation

        # Check for max discount
        if "max_discount_percent" in guardrail_def:
            violation = self._check_discount_bounds(
                guardrail_def["max_discount_percent"],
                response,
                guardrail_def.get("action_on_violation"),
            )
            if violation:
                return violation

        # Check for required escalation
        if "require_human_escalation_on" in guardrail_def:
            escalation_triggers = guardrail_def["require_human_escalation_on"]
            violation = self._check_escalation_required(
                escalation_triggers,
                response,
                guardrail_def.get("action_on_violation"),
            )
            if violation:
                return violation

        # Check for no false promises
        if "no_false_promises" in guardrail_def:
            violation = self._check_false_promises(
                response, guardrail_def.get("action_on_violation")
            )
            if violation:
                return violation

        return None

    def _check_forbidden_phrases(
        self, phrases: List[str], response: str, action: Optional[str]
    ) -> Optional[GuardrailViolation]:
        """Check if response contains forbidden phrases."""
        response_lower = response.lower()

        for phrase in phrases:
            if phrase.lower() in response_lower:
                violation_desc = (
                    f"Response contains forbidden phrase: '{phrase}' "
                    f"(action: {action})"
                )
                return GuardrailViolation(
                    guardrail_name="forbidden_phrases",
                    guardrail_type=GuardrailType.FORBIDDEN_PHRASES,
                    violation_description=violation_desc,
                    original_response=response,
                )

        return None

    def _check_discount_bounds(
        self, max_percent: float, response: str, action: Optional[str]
    ) -> Optional[GuardrailViolation]:
        """Check if response mentions discount exceeding maximum."""
        # Look for percentage patterns in response
        percent_pattern = r"(\d+(?:\.\d+)?)\s*%"
        matches = re.findall(percent_pattern, response)

        for match in matches:
            discount_value = float(match)
            if discount_value > max_percent:
                violation_desc = (
                    f"Response implies discount {discount_value}% exceeds "
                    f"maximum {max_percent}% (action: {action})"
                )
                return GuardrailViolation(
                    guardrail_name="max_discount_percent",
                    guardrail_type=GuardrailType.NUMERIC_BOUNDS,
                    violation_description=violation_desc,
                    original_response=response,
                )

        return None

    def _check_escalation_required(
        self,
        escalation_triggers: List[str],
        response: str,
        action: Optional[str],
    ) -> Optional[GuardrailViolation]:
        """Check if response should trigger mandatory escalation."""
        response_lower = response.lower()

        # Map trigger names to keywords to search for
        trigger_keywords = {
            "disability_accommodation": ["disability", "accommodation", "ada"],
            "legal_mention": ["legal", "lawsuit", "court", "attorney", "lawyer"],
            "regulatory_complaint": ["regulatory", "complaint", "ftc", "fcc", "sec"],
        }

        for trigger in escalation_triggers:
            # Use mapped keywords if available, otherwise use trigger name
            keywords = trigger_keywords.get(trigger, [trigger.lower().replace("_", " ")])

            for keyword in keywords:
                if keyword in response_lower:
                    violation_desc = (
                        f"Response contains escalation trigger '{trigger}' "
                        f"(keyword: '{keyword}') - mandatory human escalation required "
                        f"(action: {action})"
                    )
                    return GuardrailViolation(
                        guardrail_name="require_human_escalation_on",
                        guardrail_type=GuardrailType.ESCALATION_REQUIRED,
                        violation_description=violation_desc,
                        original_response=response,
                    )

        return None

    def _check_false_promises(
        self, response: str, action: Optional[str]
    ) -> Optional[GuardrailViolation]:
        """Check if response makes false promises."""
        false_promise_phrases = [
            "guarantee",
            "guaranteed",
            "definitely will",
            "definitely won't",
            "i promise",
            "will definitely",
            "won't happen",
            "100% sure",
        ]

        response_lower = response.lower()

        for phrase in false_promise_phrases:
            if phrase in response_lower:
                violation_desc = (
                    f"Response contains false promise phrase: '{phrase}' "
                    f"(action: {action})"
                )
                return GuardrailViolation(
                    guardrail_name="no_false_promises",
                    guardrail_type=GuardrailType.FORBIDDEN_PHRASES,
                    violation_description=violation_desc,
                    original_response=response,
                )

        return None

    def _log_violation(
        self,
        violation: GuardrailViolation,
        skill_id: str,
        conversation_id: str,
        turn_number: int,
        original_response: str,
    ):
        """Log violation to database."""
        violation_schema = GuardrailViolationSchema(
            conversation_id=conversation_id,
            turn_number=turn_number,
            skill_id=skill_id,
            guardrail_name=violation.guardrail_name,
            guardrail_type=violation.guardrail_type.value,
            violation_description=violation.violation_description,
            original_response=original_response,
            regenerated_response=None,
            regeneration_successful=False,
            regeneration_attempt=1,
        )

        violation_id = self.db_manager.log_violation(violation_schema)
        logger.warning(
            f"Guardrail violation logged (ID: {violation_id}): "
            f"{violation.guardrail_name} in skill {skill_id}"
        )

        # Add to in-memory log
        self.violations_log.append(violation)

    def regenerate_response(
        self,
        violation: GuardrailViolation,
        original_prompt: str,
        attempt: int = 1,
    ) -> str:
        """
        Regenerate response with violation as negative constraint.

        Calls claude-sonnet-4-6 via OpenRouter with:
        original_prompt + negative_constraint about the violation
        """
        if attempt > self.max_regeneration_attempts:
            return ""

        try:
            from anthropic import Anthropic
            import os

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                logger.error("OPENROUTER_API_KEY not set - cannot regenerate response")
                return ""

            client = Anthropic(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )

            # Build regeneration prompt with constraint
            constraint = (
                f"\n\n[GUARDRAIL VIOLATION DETECTED - PLEASE REGENERATE]\n"
                f"Previous response violated: {violation.guardrail_name}\n"
                f"Issue: {violation.violation_description}\n"
                f"Regenerate the response addressing this violation.\n"
            )

            regeneration_prompt = original_prompt + constraint

            # Call Claude Sonnet 4.6 via OpenRouter for regeneration
            message = client.messages.create(
                model="anthropic/claude-sonnet-4.6",
                max_tokens=1024,
                messages=[{"role": "user", "content": regeneration_prompt}],
            )

            regenerated = message.content[0].text
            logger.info(
                f"Regenerated response on attempt {attempt} for guardrail {violation.guardrail_name}"
            )
            return regenerated

        except Exception as e:
            logger.error(f"Error calling OpenRouter for regeneration: {str(e)}")
            return ""

    def enforce(
        self,
        skill_id: str,
        response: str,
        conversation_id: str,
        turn_number: int,
        prompt: str = "",
    ) -> Tuple[bool, str, Optional[GuardrailViolation]]:
        """
        Enforce all guardrails on an LLM response.

        Returns:
            (success, final_response, violation)
            - success: True if response passes all guardrails
            - final_response: Original or regenerated response
            - violation: The violation that triggered regeneration, if any
        """
        is_valid, violation = self.check_response(
            skill_id, response, conversation_id, turn_number
        )

        if is_valid:
            logger.info(f"Response passed all guardrails for skill {skill_id}")
            return True, response, None

        logger.warning(
            f"Guardrail violation detected in {skill_id}: "
            f"{violation.guardrail_name}"
        )

        # Try to regenerate
        for attempt in range(1, self.max_regeneration_attempts + 1):
            regenerated = self.regenerate_response(violation, prompt, attempt)

            # If regeneration failed (empty response), skip to next attempt
            if not regenerated:
                logger.warning(f"Regeneration attempt {attempt} returned empty response")
                continue

            # Check regenerated response
            is_valid, new_violation = self.check_response(
                skill_id, regenerated, conversation_id, turn_number
            )

            if is_valid:
                logger.info(
                    f"Successfully regenerated response on attempt {attempt} "
                    f"for skill {skill_id}"
                )
                return True, regenerated, violation

        # All regeneration attempts failed
        logger.error(
            f"Failed to regenerate valid response after "
            f"{self.max_regeneration_attempts} attempts for skill {skill_id}"
        )
        return False, "", violation

    def get_violations(self) -> List[GuardrailViolation]:
        """Get all logged violations."""
        return self.violations_log

    def get_violation_stats(self) -> Dict[str, int]:
        """Get statistics about violations."""
        stats = {}
        for violation in self.violations_log:
            key = violation.guardrail_name
            stats[key] = stats.get(key, 0) + 1
        return stats

    def clear_log(self):
        """Clear in-memory violation log."""
        self.violations_log.clear()
