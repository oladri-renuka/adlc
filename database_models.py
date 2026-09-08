"""Database models for conversation logging and guardrail violations."""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, Boolean
from sqlalchemy.orm import declarative_base, Session
from pydantic import BaseModel

Base = declarative_base()


class GuardrailViolation(Base):
    """ORM model for logging guardrail violations."""
    __tablename__ = "guardrail_violations"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    skill_id = Column(String(100), nullable=False)
    guardrail_name = Column(String(100), nullable=False)
    guardrail_type = Column(String(50), nullable=False)
    violation_description = Column(Text, nullable=True)
    original_response = Column(Text, nullable=False)
    regenerated_response = Column(Text, nullable=True)
    regeneration_successful = Column(Boolean, default=False)
    regeneration_attempt = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class ConversationTurn(Base):
    """ORM model for conversation history."""
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    speaker = Column(String(50), nullable=False)  # "user" or "agent"
    skill_id = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)
    guardrail_violations_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class SkillMetrics(Base):
    """ORM model for tracking skill performance metrics."""
    __tablename__ = "skill_metrics"

    id = Column(Integer, primary_key=True)
    skill_id = Column(String(100), nullable=False, unique=True, index=True)
    total_invocations = Column(Integer, default=0)
    successful_completions = Column(Integer, default=0)
    guardrail_violations = Column(Integer, default=0)
    escalations_to_human = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class GuardrailMetrics(Base):
    """ORM model for tracking individual guardrail performance."""
    __tablename__ = "guardrail_metrics"

    id = Column(Integer, primary_key=True)
    guardrail_name = Column(String(100), nullable=False, unique=True, index=True)
    guardrail_type = Column(String(50), nullable=False)
    total_violations = Column(Integer, default=0)
    successful_regenerations = Column(Integer, default=0)
    failed_regenerations = Column(Integer, default=0)
    violation_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


# Pydantic models for API/validation

class GuardrailViolationSchema(BaseModel):
    """Pydantic model for guardrail violation data."""
    conversation_id: str
    turn_number: int
    skill_id: str
    guardrail_name: str
    guardrail_type: str
    violation_description: Optional[str] = None
    original_response: str
    regenerated_response: Optional[str] = None
    regeneration_successful: bool = False
    regeneration_attempt: int = 1

    class Config:
        from_attributes = True


class ConversationTurnSchema(BaseModel):
    """Pydantic model for conversation turn."""
    conversation_id: str
    turn_number: int
    speaker: str  # "user" or "agent"
    skill_id: Optional[str] = None
    text: str
    guardrail_violations_count: int = 0

    class Config:
        from_attributes = True


class SkillMetricsSchema(BaseModel):
    """Pydantic model for skill metrics."""
    skill_id: str
    total_invocations: int = 0
    successful_completions: int = 0
    guardrail_violations: int = 0
    escalations_to_human: int = 0
    success_rate: float = 0.0

    class Config:
        from_attributes = True


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, db_path: str = "sqlite:///adlc_framework.db"):
        """Initialize database connection."""
        self.engine = create_engine(db_path, echo=False)
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=self.engine)
        return SessionLocal()

    def log_violation(self, violation: GuardrailViolationSchema):
        """Log a guardrail violation."""
        session = self.get_session()
        try:
            db_violation = GuardrailViolation(**violation.dict())
            session.add(db_violation)
            session.commit()
            return db_violation.id
        finally:
            session.close()

    def log_turn(self, turn: ConversationTurnSchema):
        """Log a conversation turn."""
        session = self.get_session()
        try:
            db_turn = ConversationTurn(**turn.dict())
            session.add(db_turn)
            session.commit()
            return db_turn.id
        finally:
            session.close()

    def update_skill_metrics(self, skill_id: str, metrics: dict):
        """Update skill metrics."""
        session = self.get_session()
        try:
            metric = session.query(SkillMetrics).filter_by(skill_id=skill_id).first()
            if not metric:
                metric = SkillMetrics(skill_id=skill_id)
                session.add(metric)

            for key, value in metrics.items():
                if hasattr(metric, key):
                    setattr(metric, key, value)

            metric.last_updated = datetime.utcnow()
            session.commit()
        finally:
            session.close()

    def get_violations_for_conversation(self, conversation_id: str):
        """Get all violations for a conversation."""
        session = self.get_session()
        try:
            violations = session.query(GuardrailViolation).filter_by(
                conversation_id=conversation_id
            ).order_by(GuardrailViolation.timestamp).all()
            return violations
        finally:
            session.close()

    def get_skill_metrics(self, skill_id: str) -> Optional[SkillMetricsSchema]:
        """Get metrics for a specific skill."""
        session = self.get_session()
        try:
            metric = session.query(SkillMetrics).filter_by(skill_id=skill_id).first()
            if metric:
                return SkillMetricsSchema.from_orm(metric)
            return None
        finally:
            session.close()

    def get_guardrail_violation_rate(self, guardrail_name: str) -> float:
        """Get violation rate for a guardrail."""
        session = self.get_session()
        try:
            metric = session.query(GuardrailMetrics).filter_by(
                guardrail_name=guardrail_name
            ).first()
            if metric:
                return metric.violation_rate
            return 0.0
        finally:
            session.close()
