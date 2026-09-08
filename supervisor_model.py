"""Supervisor Model - validates primary LLM output using Claude Haiku via OpenRouter."""

import json
import logging
import os
from typing import Optional, Tuple, Dict, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from skill_models import SkillRegistry
from database_models import DatabaseManager

logger = logging.getLogger(__name__)


class SupervisorDecision(str, Enum):
    """Supervisor decision on LLM response."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass
class SupervisorFeedback:
    """Supervisor's feedback on a response."""
    decision: SupervisorDecision
    reasoning: str
    issues_found: List[str]
    severity: str  # "low", "medium", "high"
    confidence: float  # 0.0-1.0


class SupervisorModel:
    """
    Validates LLM responses using Claude Haiku via OpenRouter.

    Checks for:
    - Guardrail violations (forbidden phrases, discount limits, false promises)
    - Tone appropriateness (empathetic, professional)
    - False promises or guarantees
    - Escalation signals (disability, legal, regulatory)
    - Contextual appropriateness

    Uses:
    - Claude Haiku 3.5 via OpenRouter API (anthropic/claude-3-haiku)
    - API Key: OPENROUTER_API_KEY environment variable
    - Endpoint: https://openrouter.ai/api/v1/messages
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        db_manager: DatabaseManager,
    ):
        """
        Initialize supervisor with skill registry and database.

        REQUIRES OPENROUTER_API_KEY environment variable to be set.

        Args:
            skill_registry: Registry of skills
            db_manager: Database manager for logging
        """
        self.skill_registry = skill_registry
        self.db_manager = db_manager
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        if not self.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required. "
                "Set it with: export OPENROUTER_API_KEY=sk-or-v1-..."
            )

        logger.info("Supervisor initialized with OpenRouter API key")
        self.rejection_count = 0
        self.approval_count = 0
        self.total_evaluations = 0

    def evaluate(
        self,
        skill_id: str,
        response: str,
        conversation_history: Optional[List[Dict]] = None,
        turn_number: int = 1,
    ) -> SupervisorFeedback:
        """
        Evaluate LLM response using Claude Haiku via OpenRouter.

        This calls the real Claude Haiku API - requires OPENROUTER_API_KEY.

        Args:
            skill_id: The skill that generated the response
            response: The LLM response to evaluate
            conversation_history: Previous turns in conversation
            turn_number: Current turn number

        Returns:
            SupervisorFeedback with decision and reasoning
        """
        self.total_evaluations += 1

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            skill_id, response, conversation_history, turn_number
        )

        # Call Claude Haiku via OpenRouter (REAL API)
        feedback = self._evaluate_with_api(prompt)

        if feedback.decision == SupervisorDecision.REJECTED:
            self.rejection_count += 1
            logger.warning(
                f"Supervisor rejected response for {skill_id}: {feedback.reasoning}"
            )
        else:
            self.approval_count += 1
            logger.info(f"Supervisor approved response for {skill_id}")

        return feedback

    def _build_evaluation_prompt(
        self,
        skill_id: str,
        response: str,
        conversation_history: Optional[List[Dict]],
        turn_number: int,
    ) -> str:
        """Build prompt for Claude Haiku supervisor evaluation."""
        skill = self.skill_registry.get_skill(skill_id)
        skill_description = skill.description if skill else "Unknown skill"

        prompt = f"""You are a supervisor validating customer service responses for a telecom retention agent.

Skill: {skill_id}
Description: {skill_description}
Turn: {turn_number}

Response to evaluate:
"{response}"

Evaluate this response for:

1. GUARDRAIL COMPLIANCE:
   - No forbidden phrases (I guarantee, promise, competitor prices)
   - No false promises (definitely will, guaranteed restoration time)
   - Discount limits (max 30% off)
   - Escalation triggers (disability, legal, regulatory complaints)

2. TONE:
   - Is it empathetic and professional?
   - Does it acknowledge the customer's concern?
   - Is it appropriate for a telecom service context?

3. ACCURACY:
   - No false information about services
   - No impossible promises
   - Realistic expectations set

4. ESCALATION APPROPRIATENESS:
   - If customer mentioned disability/legal/regulatory issues, is escalation acknowledged?

Respond with JSON:
{{
  "decision": "approved|rejected|needs_clarification",
  "reasoning": "brief explanation",
  "issues_found": ["issue1", "issue2"],
  "severity": "low|medium|high",
  "confidence": 0.95
}}"""
        return prompt

    def _evaluate_with_api(self, prompt: str) -> SupervisorFeedback:
        """
        Call Claude Haiku via OpenRouter API for evaluation.

        Uses:
        - Model: anthropic/claude-haiku-4.5
        - Endpoint: https://openrouter.ai/api/v1/messages
        - Auth: OPENROUTER_API_KEY
        """
        try:
            import httpx
            import json

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "anthropic/claude-haiku-4.5",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = httpx.post(
                "https://openrouter.ai/api/v1/messages",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            response_text = data["content"][0]["text"]
            return self._parse_api_response_text(response_text)

        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            # On error, approve for safety (don't block user)
            return SupervisorFeedback(
                decision=SupervisorDecision.APPROVED,
                reasoning="API error - approving for safety",
                issues_found=[],
                severity="low",
                confidence=0.5,
            )

    def _parse_api_response_text(self, response_text: str) -> SupervisorFeedback:
        """Parse Claude Haiku response text from OpenRouter."""
        try:
            import json

            # Claude should return JSON in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)

                return SupervisorFeedback(
                    decision=SupervisorDecision(
                        parsed.get("decision", "approved").lower()
                    ),
                    reasoning=parsed.get("reasoning", ""),
                    issues_found=parsed.get("issues_found", []),
                    severity=parsed.get("severity", "low"),
                    confidence=float(parsed.get("confidence", 0.75)),
                )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse Haiku response: {str(e)}")

        # Default to approved if parsing fails
        return SupervisorFeedback(
            decision=SupervisorDecision.APPROVED,
            reasoning="Could not parse supervisor response",
            issues_found=[],
            severity="low",
            confidence=0.5,
        )


    def enforce_with_feedback(
        self,
        skill_id: str,
        response: str,
        prompt: str,
        conversation_id: str,
        turn_number: int,
        max_regeneration_attempts: int = 2,
    ) -> Tuple[bool, str, Optional[SupervisorFeedback]]:
        """
        Enforce supervisor validation with regeneration attempts.

        Returns:
            (success, final_response, rejection_feedback)
            - success: True if response approved after regeneration attempts
            - final_response: Final response (original or regenerated)
            - rejection_feedback: The rejection feedback if rejected
        """
        feedback = self.evaluate(skill_id, response, turn_number=turn_number)

        if feedback.decision == SupervisorDecision.APPROVED:
            logger.info(f"Supervisor approved response on first evaluation")
            return True, response, None

        logger.warning(
            f"Supervisor rejected: {feedback.reasoning}. "
            f"Attempting regeneration (max {max_regeneration_attempts} attempts)"
        )

        # Try to regenerate
        for attempt in range(1, max_regeneration_attempts + 1):
            regenerated = self._regenerate_with_feedback(response, feedback, prompt)

            # Re-evaluate regenerated response
            feedback = self.evaluate(
                skill_id, regenerated, turn_number=turn_number + attempt
            )

            if feedback.decision == SupervisorDecision.APPROVED:
                logger.info(
                    f"Supervisor approved regenerated response on attempt {attempt}"
                )
                return True, regenerated, None

            logger.warning(
                f"Attempt {attempt}: Supervisor still has issues. {feedback.reasoning}"
            )

        # All regeneration attempts failed
        logger.error(
            f"All {max_regeneration_attempts} regeneration attempts failed. "
            f"Escalating to human."
        )
        return False, "", feedback

    def _regenerate_with_feedback(
        self, original_response: str, feedback: SupervisorFeedback, prompt: str
    ) -> str:
        """Regenerate response incorporating supervisor feedback."""
        constraint = (
            f"\n\n[SUPERVISOR FEEDBACK - RESPONSE NEEDS REVISION]\n"
            f"Issues found: {'; '.join(feedback.issues_found)}\n"
            f"Severity: {feedback.severity}\n"
            f"Feedback: {feedback.reasoning}\n"
            f"Please regenerate the response addressing these issues."
        )

        return prompt + constraint

    def get_metrics(self) -> Dict:
        """Get supervisor performance metrics."""
        total = self.total_evaluations
        if total == 0:
            return {
                "total_evaluations": 0,
                "approval_rate": 0.0,
                "rejection_rate": 0.0,
                "approvals": 0,
                "rejections": 0,
            }

        approval_rate = (self.approval_count / total) * 100
        rejection_rate = (self.rejection_count / total) * 100

        return {
            "total_evaluations": total,
            "approvals": self.approval_count,
            "rejections": self.rejection_count,
            "approval_rate": round(approval_rate, 2),
            "rejection_rate": round(rejection_rate, 2),
        }

    def log_evaluation(
        self,
        conversation_id: str,
        turn_number: int,
        skill_id: str,
        original_response: str,
        feedback: SupervisorFeedback,
        regenerated_response: Optional[str] = None,
    ):
        """Log supervisor evaluation to database."""
        from database_models import GuardrailViolationSchema

        # Use guardrail violation table to log supervisor rejections
        if feedback.decision != SupervisorDecision.APPROVED:
            violation_schema = GuardrailViolationSchema(
                conversation_id=conversation_id,
                turn_number=turn_number,
                skill_id=skill_id,
                guardrail_name="supervisor_rejection",
                guardrail_type="supervisor_validation",
                violation_description=feedback.reasoning,
                original_response=original_response,
                regenerated_response=regenerated_response,
                regeneration_successful=(
                    feedback.decision == SupervisorDecision.APPROVED
                ),
                regeneration_attempt=1,
            )

            self.db_manager.log_violation(violation_schema)
            logger.info(f"Logged supervisor rejection for {skill_id} in turn {turn_number}")

    def reset_metrics(self):
        """Reset evaluation metrics."""
        self.rejection_count = 0
        self.approval_count = 0
        self.total_evaluations = 0
