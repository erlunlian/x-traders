"""
AI Agent SQLModel database models
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DECIMAL, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM, UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

from enums import AgentAction, AgentDecisionTrigger, AgentMemoryType, AgentThoughtType, LLMModel


class AIAgent(SQLModel, table=True):
    """AI trading agent configuration"""
    __tablename__ = "ai_agents"

    agent_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    name: str = Field(sa_column=Column(String(100), nullable=False, unique=True))
    trader_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("trader_accounts.trader_id"), nullable=False)
    )
    
    # Model configuration
    llm_model: LLMModel = Field(
        sa_column=Column(ENUM(LLMModel, name="llm_model", create_constraint=True), nullable=False)
    )
    temperature: float = Field(
        default=0.7,
        sa_column=Column(DECIMAL(3, 2), default=0.7),
    )
    system_prompt: str = Field(sa_column=Column(String(5000), nullable=False))
    
    # Status
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True))
    
    # Basic tracking
    total_decisions: int = Field(default=0, sa_column=Column(Integer, default=0))
    last_decision_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    
    # Tweet processing tracking
    last_processed_tweet_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )
    
    # Relationships
    decisions: List["AgentDecision"] = Relationship(back_populates="agent", cascade_delete=True)
    memory_snapshots: List["AgentMemory"] = Relationship(back_populates="agent", cascade_delete=True)

    class Config:
        arbitrary_types_allowed = True


class AgentDecision(SQLModel, table=True):
    """Agent decision tracking"""
    __tablename__ = "agent_decisions"

    decision_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )
    
    # What triggered this decision
    trigger_type: AgentDecisionTrigger = Field(
        default=AgentDecisionTrigger.AUTONOMOUS,
        sa_column=Column(
            ENUM(AgentDecisionTrigger, name="agent_decision_trigger", create_constraint=True),
            nullable=False,
            default=AgentDecisionTrigger.AUTONOMOUS,
        ),
    )
    trigger_tweet_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100), ForeignKey("x_tweets.tweet_id"), nullable=True),
    )
    
    # The decision
    action: AgentAction = Field(
        sa_column=Column(ENUM(AgentAction, name="agent_action", create_constraint=True), nullable=False)
    )
    ticker: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, index=True))
    quantity: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    reasoning: Optional[str] = Field(default=None, sa_column=Column(String(2000), nullable=True))
    
    # Execution (for trade actions)
    order_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("orders.order_id"), nullable=True),
    )
    executed: bool = Field(default=False, sa_column=Column(Boolean, default=False))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )
    
    # Relationships
    agent: Optional[AIAgent] = Relationship(back_populates="decisions")
    thoughts: List["AgentThought"] = Relationship(back_populates="decision", cascade_delete=True)

    class Config:
        arbitrary_types_allowed = True


class AgentThought(SQLModel, table=True):
    """Individual thoughts in decision process"""
    __tablename__ = "agent_thoughts"

    thought_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    decision_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("agent_decisions.decision_id"), nullable=True),
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )
    
    step_number: int = Field(sa_column=Column(Integer, nullable=False))
    thought_type: AgentThoughtType = Field(
        sa_column=Column(
            ENUM(AgentThoughtType, name="agent_thought_type", create_constraint=True),
            nullable=False,
        )
    )
    content: str = Field(sa_column=Column(String(2000), nullable=False))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )
    
    # Relationship
    decision: Optional[AgentDecision] = Relationship(back_populates="thoughts")

    class Config:
        arbitrary_types_allowed = True


class AgentMemory(SQLModel, table=True):
    """Agent memory storage with compression"""
    __tablename__ = "agent_memory"

    memory_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )
    
    memory_type: AgentMemoryType = Field(
        sa_column=Column(
            ENUM(AgentMemoryType, name="agent_memory_type", create_constraint=True),
            nullable=False,
        )
    )
    content: str = Field(sa_column=Column(String(10000), nullable=False))
    token_count: int = Field(sa_column=Column(Integer, nullable=False))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )
    
    # Relationship
    agent: Optional[AIAgent] = Relationship(back_populates="memory_snapshots")

    class Config:
        arbitrary_types_allowed = True