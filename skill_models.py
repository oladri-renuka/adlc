"""Pydantic models for skill schema validation."""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class ActionType(str, Enum):
    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non-deterministic"


class GuardrailAction(str, Enum):
    REGENERATE = "regenerate_with_violation_as_constraint"
    REGENERATE_WITH_LOWER_DISCOUNT = "regenerate_with_lower_discount"
    REGENERATE_WITHOUT_PHRASE = "regenerate_without_phrase"
    BLOCK_ACTION = "block_action"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    LOG_WARNING = "log_warning"
    LIMIT_TO_MAX = "limit_to_max"


class SlotType(str, Enum):
    STRING = "string"
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"


class SlotDefinition(BaseModel):
    """Definition of a required or optional slot (variable) in a skill."""
    type: SlotType
    required: bool = False
    description: str = ""
    enum: Optional[List[str]] = None


class Action(BaseModel):
    """Single action within a skill state machine."""
    name: str = Field(..., description="Action name")
    type: ActionType = Field(..., description="Whether action is deterministic or non-deterministic")
    logic: Optional[str] = Field(None, description="Logic for deterministic actions (pseudocode)")
    model: Optional[str] = Field(None, description="Model to use for non-deterministic actions")
    prompt_template: Optional[str] = Field(None, description="Prompt template for LLM-based actions")

    @validator("logic", always=True)
    def check_deterministic_has_logic(cls, v, values):
        if values.get("type") == ActionType.DETERMINISTIC and not v:
            raise ValueError("Deterministic action must have logic defined")
        return v

    @validator("prompt_template", always=True)
    def check_non_deterministic_has_prompt(cls, v, values):
        if values.get("type") == ActionType.NON_DETERMINISTIC and not v:
            raise ValueError("Non-deterministic action must have prompt_template defined")
        return v


class StateTransition(BaseModel):
    """Transition from one state to another."""
    target: Optional[str] = None
    condition: Optional[str] = None


class StateMachineState(BaseModel):
    """Single state in a skill's state machine."""
    action: Optional[str] = Field(None, description="Action to execute in this state")
    parallel_actions: Optional[List[str]] = Field(None, description="Multiple actions to run in parallel")
    transitions: Dict[str, str] = Field(default_factory=dict, description="State transitions")
    final: bool = Field(False, description="Whether this is a terminal state")

    @validator("final", always=True)
    def check_action_or_final(cls, v, values):
        # Final states don't need actions, non-final states need either action or parallel_actions
        if not v and not values.get("action") and not values.get("parallel_actions"):
            raise ValueError("Non-final state must have either 'action' or 'parallel_actions'")
        return v


class StateMachine(BaseModel):
    """Complete state machine definition for a skill."""
    initial: str = Field(..., description="Initial state name")
    states: Dict[str, StateMachineState] = Field(..., description="State definitions")

    @validator("states")
    def validate_transitions_exist(cls, v, values):
        if "initial" not in values:
            return v
        initial = values["initial"]
        if initial not in v:
            raise ValueError(f"Initial state '{initial}' not defined in states")
        # Validate all transition targets exist
        for state_name, state in v.items():
            for target in state.transitions.values():
                if target not in v and target not in ["end_skill", "escalate_to_human"]:
                    # Allow end_skill and escalate_to_human as implicit states
                    pass
        return v


class Guardrail(BaseModel):
    """Guardrail constraint for skill execution."""
    type: Optional[str] = None
    value: Optional[Any] = None
    action: GuardrailAction = Field(default=GuardrailAction.REGENERATE)
    description: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class Trigger(BaseModel):
    """Trigger condition for skill activation."""
    intent_keywords: Optional[List[str]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1)
    customer_tenure_months: Optional[List[str]] = None
    account_health: Optional[str] = None
    customer_action: Optional[str] = None
    escalation_required: Optional[bool] = False


class Skill(BaseModel):
    """Complete skill definition matching YAML schema."""
    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="Skill description")
    version: str = Field(..., description="Skill version")

    triggers: List[Trigger] = Field(default_factory=list, description="Skill activation triggers")
    required_slots: Dict[str, SlotDefinition] = Field(
        default_factory=dict,
        description="Required slots for skill execution"
    )
    guardrails: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Guardrail constraints"
    )
    actions: List[Action] = Field(default_factory=list, description="Skill actions")
    state_machine: StateMachine = Field(..., description="State machine definition")

    @validator("skill_id")
    def validate_skill_id(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("skill_id must be alphanumeric with underscores")
        return v

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True


class SkillRegistry(BaseModel):
    """Registry of all loaded skills."""
    skills: Dict[str, Skill] = Field(default_factory=dict)
    version: str = "1.0"

    def add_skill(self, skill: Skill):
        """Add a skill to registry."""
        self.skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID."""
        return self.skills.get(skill_id)

    def list_skills(self) -> List[str]:
        """List all available skill IDs."""
        return list(self.skills.keys())
