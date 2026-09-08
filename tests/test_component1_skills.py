"""Tests for Component 1: Declarative Skills Engine."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_models import (
    Skill, SkillRegistry, Action, ActionType, StateMachineState,
    Trigger, SlotDefinition, SlotType, GuardrailAction
)
from skill_parser import SkillParser, SkillParseError, load_skills


class TestSkillModels:
    """Test Pydantic models for skill schema validation."""

    def test_action_deterministic_requires_logic(self):
        """Deterministic actions must have logic defined."""
        with pytest.raises(ValueError, match="Deterministic action must have logic"):
            Action(
                name="test_action",
                type=ActionType.DETERMINISTIC,
                logic=None
            )

    def test_action_non_deterministic_requires_prompt(self):
        """Non-deterministic actions must have prompt_template."""
        with pytest.raises(ValueError, match="Non-deterministic action must have"):
            Action(
                name="test_action",
                type=ActionType.NON_DETERMINISTIC,
                logic="some logic"
            )

    def test_action_valid_deterministic(self):
        """Valid deterministic action."""
        action = Action(
            name="test_action",
            type=ActionType.DETERMINISTIC,
            logic="if x: return y"
        )
        assert action.type == ActionType.DETERMINISTIC
        assert action.logic == "if x: return y"

    def test_action_valid_non_deterministic(self):
        """Valid non-deterministic action."""
        action = Action(
            name="llm_action",
            type=ActionType.NON_DETERMINISTIC,
            model="claude-sonnet-4-6",
            prompt_template="Generate a message"
        )
        assert action.type == ActionType.NON_DETERMINISTIC
        assert action.prompt_template == "Generate a message"

    def test_slot_definition_required_and_typed(self):
        """Slot definitions have type and required flag."""
        slot = SlotDefinition(
            type=SlotType.STRING,
            required=True,
            description="Customer ID"
        )
        assert slot.type == SlotType.STRING
        assert slot.required is True

    def test_state_machine_initial_state_must_exist(self):
        """Initial state must be defined in states."""
        from skill_models import StateMachine
        with pytest.raises(ValueError, match="Initial state"):
            StateMachine(
                initial="start",
                states={
                    "other": StateMachineState(action="foo", transitions={})
                }
            )

    def test_skill_id_validation(self):
        """Skill IDs must be alphanumeric with underscores."""
        from skill_models import StateMachine
        with pytest.raises(ValueError, match="alphanumeric"):
            Skill(
                skill_id="invalid-skill",  # dashes not allowed
                name="Test",
                description="Test",
                version="1.0",
                state_machine=StateMachine(
                    initial="start",
                    states={"start": StateMachineState(action="test", transitions={})}
                )
            )

    def test_valid_skill_structure(self):
        """Valid skill can be created."""
        from skill_models import StateMachine
        skill = Skill(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            version="1.0",
            triggers=[Trigger(intent_keywords=["test"])],
            required_slots={
                "account_id": SlotDefinition(type=SlotType.STRING, required=True)
            },
            actions=[
                Action(
                    name="action1",
                    type=ActionType.DETERMINISTIC,
                    logic="return True"
                )
            ],
            state_machine=StateMachine(
                initial="start",
                states={
                    "start": StateMachineState(action="action1", transitions={"success": "end"}),
                    "end": StateMachineState(final=True)
                }
            )
        )
        assert skill.skill_id == "test_skill"
        assert len(skill.actions) == 1


class TestSkillParser:
    """Test skill parser that loads and validates YAML."""

    def test_parser_initialization(self):
        """Parser initializes with skills directory."""
        parser = SkillParser("skills")
        assert parser.skills_dir.name == "skills"

    def test_load_all_skills(self):
        """Load all skills from skills directory."""
        parser = SkillParser("skills")
        registry = parser.load_all_skills()

        # Should load all 5 required skills
        assert len(registry.skills) >= 5, f"Expected at least 5 skills, got {len(registry.skills)}"

        # Check that all required skills are present
        required_skills = {
            "retention_offer",
            "plan_downgrade",
            "pause_service",
            "technical_escalation",
            "account_lookup"
        }
        loaded_skills = set(registry.list_skills())
        assert required_skills.issubset(loaded_skills), \
            f"Missing skills: {required_skills - loaded_skills}"

    def test_get_skill_by_id(self):
        """Retrieve a specific skill by ID."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        skill = parser.get_skill("retention_offer")
        assert skill is not None
        assert skill.skill_id == "retention_offer"
        assert skill.name == "Retention Offer"

    def test_skill_has_required_components(self):
        """Each skill has required components."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            assert skill.skill_id == skill_id
            assert skill.name, f"Skill {skill_id} has no name"
            assert skill.description, f"Skill {skill_id} has no description"
            assert skill.version, f"Skill {skill_id} has no version"
            assert skill.state_machine, f"Skill {skill_id} has no state machine"
            assert skill.state_machine.initial, f"Skill {skill_id} has no initial state"

    def test_retention_offer_skill_structure(self):
        """Retention offer skill has correct structure."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        skill = parser.get_skill("retention_offer")
        assert skill is not None

        # Check actions
        action_names = {a.name for a in skill.actions}
        assert "check_offer_eligibility" in action_names
        assert "calculate_offer" in action_names
        assert "generate_retention_message" in action_names

        # Check guardrails
        assert skill.guardrails, "Retention offer should have guardrails"

        # Check state machine
        assert skill.state_machine.initial == "check_eligibility"

    def test_pause_service_skill_structure(self):
        """Pause service skill has correct structure."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        skill = parser.get_skill("pause_service")
        assert skill is not None

        # Check that skill has eligibility check (deterministic)
        action_names = {a.name for a in skill.actions}
        assert "check_pause_eligibility" in action_names

        # Find the action and verify it's deterministic
        eligibility_action = next(a for a in skill.actions if a.name == "check_pause_eligibility")
        assert eligibility_action.type == ActionType.DETERMINISTIC
        assert eligibility_action.logic is not None

    def test_technical_escalation_skill_structure(self):
        """Technical escalation skill has correct structure."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        skill = parser.get_skill("technical_escalation")
        assert skill is not None

        # Check actions
        action_names = {a.name for a in skill.actions}
        assert "classify_issue" in action_names
        assert "create_ticket" in action_names

        # Check guardrails
        assert skill.guardrails, "Technical escalation should have guardrails"

    def test_state_machine_transitions_valid(self):
        """All state machine transitions point to valid states."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            state_names = set(skill.state_machine.states.keys())

            for state_name, state in skill.state_machine.states.items():
                for target in state.transitions.values():
                    # Target must be a valid state or an implicit end state
                    assert (
                        target in state_names
                        or target in ["end_skill", "escalate_to_human"]
                    ), f"Skill {skill_id}: state {state_name} has invalid transition to {target}"

    def test_all_referenced_actions_exist(self):
        """All actions referenced in state machine exist."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            consistency_issues = parser.validate_skill_consistency(skill)

            # Check for missing action references
            action_issues = [i for i in consistency_issues if "undefined action" in i]
            assert not action_issues, \
                f"Skill {skill_id} has undefined action references: {action_issues}"

    def test_consistency_validation(self):
        """Consistency validation detects issues."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            issues = parser.validate_skill_consistency(skill)
            # Should be no critical issues for loaded skills
            critical_issues = [i for i in issues if "undefined" in i.lower()]
            assert not critical_issues, \
                f"Skill {skill_id} has critical issues: {critical_issues}"


class TestSkillRegistry:
    """Test skill registry functionality."""

    def test_skill_registry_add_and_get(self):
        """Registry can store and retrieve skills."""
        from skill_models import StateMachine
        registry = SkillRegistry()

        skill = Skill(
            skill_id="test",
            name="Test",
            description="Test skill",
            version="1.0",
            state_machine=StateMachine(
                initial="start",
                states={"start": StateMachineState(final=True)}
            )
        )

        registry.add_skill(skill)
        retrieved = registry.get_skill("test")
        assert retrieved.skill_id == "test"

    def test_skill_registry_list(self):
        """Registry can list all skills."""
        parser = SkillParser("skills")
        registry = parser.load_all_skills()

        skills = registry.list_skills()
        assert len(skills) >= 5


class TestSkillDeterminism:
    """Test that deterministic vs non-deterministic actions are correctly marked."""

    def test_deterministic_actions_never_skip_logic(self):
        """Deterministic actions always have logic."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            for action in skill.actions:
                if action.type == ActionType.DETERMINISTIC:
                    assert action.logic is not None, \
                        f"Skill {skill_id} action {action.name} is deterministic but has no logic"

    def test_non_deterministic_actions_have_prompts(self):
        """Non-deterministic actions have prompt templates."""
        parser = SkillParser("skills")
        parser.load_all_skills()

        for skill_id in parser.list_skills():
            skill = parser.get_skill(skill_id)
            for action in skill.actions:
                if action.type == ActionType.NON_DETERMINISTIC:
                    assert action.prompt_template is not None, \
                        f"Skill {skill_id} action {action.name} is non-deterministic but has no prompt"
                    assert action.model is not None, \
                        f"Skill {skill_id} action {action.name} has no model specified"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
