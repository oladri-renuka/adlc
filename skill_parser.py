"""Skill parser: loads YAML skill definitions and validates them at runtime."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import ValidationError
import logging

from skill_models import Skill, SkillRegistry, Action, StateMachineState, Trigger, SlotDefinition

logger = logging.getLogger(__name__)


class SkillParseError(Exception):
    """Raised when skill YAML parsing fails."""
    pass


class SkillParser:
    """Parses YAML skill definitions and validates against Pydantic schema."""

    def __init__(self, skills_dir: str = "skills"):
        """Initialize parser with path to skills directory."""
        self.skills_dir = Path(skills_dir)
        self.registry = SkillRegistry()
        self.errors: Dict[str, str] = {}

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")

    def load_all_skills(self) -> SkillRegistry:
        """Load and parse all YAML skill files from skills directory."""
        if not self.skills_dir.exists():
            raise SkillParseError(f"Skills directory not found: {self.skills_dir}")

        yaml_files = sorted(self.skills_dir.glob("*.yaml")) + sorted(self.skills_dir.glob("*.yml"))

        if not yaml_files:
            logger.warning(f"No YAML files found in {self.skills_dir}")
            return self.registry

        for yaml_file in yaml_files:
            try:
                logger.info(f"Loading skill from {yaml_file}")
                self._load_skill_file(yaml_file)
            except (yaml.YAMLError, ValidationError, SkillParseError) as e:
                error_msg = f"Failed to load {yaml_file.name}: {str(e)}"
                logger.error(error_msg)
                self.errors[yaml_file.name] = error_msg

        if self.errors:
            logger.warning(f"Loaded {len(self.registry.skills)} skills with {len(self.errors)} errors")
        else:
            logger.info(f"Successfully loaded {len(self.registry.skills)} skills")

        return self.registry

    def _load_skill_file(self, yaml_file: Path) -> Skill:
        """Load and parse a single YAML skill file."""
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            raise SkillParseError(f"Empty YAML file: {yaml_file}")

        # Transform YAML into Pydantic-compatible format
        skill_data = self._transform_yaml_to_skill(data)

        # Validate against Pydantic schema
        try:
            skill = Skill(**skill_data)
        except ValidationError as e:
            raise SkillParseError(f"Validation failed for {yaml_file.name}:\n{e}")

        self.registry.add_skill(skill)
        return skill

    def _transform_yaml_to_skill(self, data: Dict) -> Dict:
        """Transform raw YAML into Pydantic-compatible format."""
        transformed = {
            "skill_id": data.get("skill_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "version": data.get("version"),
        }

        # Transform triggers
        triggers_raw = data.get("triggers", [])
        transformed["triggers"] = [Trigger(**t) if isinstance(t, dict) else t for t in triggers_raw]

        # Transform required_slots
        slots_raw = data.get("required_slots", {})
        transformed["required_slots"] = {}
        if isinstance(slots_raw, dict):
            for slot_name, slot_config in slots_raw.items():
                if isinstance(slot_config, dict):
                    transformed["required_slots"][slot_name] = SlotDefinition(**slot_config)

        # Transform actions
        actions_raw = data.get("actions", [])
        transformed["actions"] = []
        for action_raw in actions_raw:
            if isinstance(action_raw, dict):
                transformed["actions"].append(Action(**action_raw))

        # Transform state_machine
        sm_raw = data.get("state_machine", {})
        if sm_raw:
            transformed["state_machine"] = {
                "initial": sm_raw.get("initial"),
                "states": self._transform_states(sm_raw.get("states", {})),
            }

        # Keep guardrails as-is (flexible format)
        transformed["guardrails"] = data.get("guardrails", [])

        return transformed

    def _transform_states(self, states_raw: Dict) -> Dict:
        """Transform state definitions."""
        transformed_states = {}
        for state_name, state_config in states_raw.items():
            if isinstance(state_config, dict):
                state_obj = {
                    "action": state_config.get("action"),
                    "parallel_actions": state_config.get("parallel_actions"),
                    "transitions": state_config.get("transitions", {}),
                    "final": state_config.get("final", False),
                }
                # Remove None values
                state_obj = {k: v for k, v in state_obj.items() if v is not None}
                transformed_states[state_name] = StateMachineState(**state_obj)
        return transformed_states

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID."""
        return self.registry.get_skill(skill_id)

    def list_skills(self) -> List[str]:
        """List all loaded skill IDs."""
        return self.registry.list_skills()

    def validate_skill_consistency(self, skill: Skill) -> List[str]:
        """Perform deeper consistency checks on skill definition."""
        issues = []

        # Check all actions referenced in state machine exist
        action_names = {a.name for a in skill.actions}
        for state_name, state in skill.state_machine.states.items():
            if state.action and state.action not in action_names:
                issues.append(f"State '{state_name}' references undefined action '{state.action}'")
            if state.parallel_actions:
                for action in state.parallel_actions:
                    if action not in action_names:
                        issues.append(
                            f"State '{state_name}' references undefined parallel action '{action}'"
                        )

        # Check all required slots are documented
        slot_names = set(skill.required_slots.keys())
        guardrail_slots = set()
        for guardrail in skill.guardrails:
            if isinstance(guardrail, dict):
                guardrail_slots.update(k for k in guardrail.keys() if k not in ["action", "type"])

        # Warn about guardrails referencing undocumented slots
        for slot in guardrail_slots:
            if slot not in slot_names:
                issues.append(f"Guardrail references undocumented slot: '{slot}'")

        # Check state machine validity
        all_states = set(skill.state_machine.states.keys())
        for state_name, state in skill.state_machine.states.items():
            for target in state.transitions.values():
                if target not in all_states and target not in ["end_skill", "escalate_to_human"]:
                    issues.append(f"State '{state_name}' transitions to undefined state '{target}'")

        return issues

    def report_errors(self) -> str:
        """Generate a report of parsing errors."""
        if not self.errors:
            return "No parsing errors."

        report = f"Skill Parsing Errors ({len(self.errors)} total):\n"
        for filename, error in self.errors.items():
            report += f"  - {filename}: {error}\n"
        return report


def load_skills(skills_dir: str = "skills") -> SkillRegistry:
    """Convenience function to load all skills."""
    parser = SkillParser(skills_dir)
    registry = parser.load_all_skills()

    # Validate consistency
    for skill_id in parser.list_skills():
        skill = parser.get_skill(skill_id)
        consistency_issues = parser.validate_skill_consistency(skill)
        if consistency_issues:
            logger.warning(f"Consistency issues in {skill_id}: {consistency_issues}")

    return registry
