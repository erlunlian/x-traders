"""
Pydantic schemas for AI agents
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from enums import AgentAction, AgentDecisionTrigger, AgentMemoryType, AgentThoughtType, LLMModel


# Request models
class CreateAgentRequest(BaseModel):
    """Request to create a new agent with a new trader"""

    name: str = Field(min_length=1, max_length=100)
    llm_model: LLMModel
    personality_prompt: str = Field(min_length=1, max_length=5000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    is_active: bool = True
    initial_balance_in_cents: int = Field(default=10000000, ge=0)  # Default $100,000


class UpdateAgentRequest(BaseModel):
    """Request to update agent configuration"""

    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    personality_prompt: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_active: Optional[bool] = None
    llm_model: Optional[LLMModel] = None


# Response models
class Agent(BaseModel):
    """Agent information"""

    agent_id: UUID
    name: str
    trader_id: UUID
    llm_model: LLMModel
    temperature: float
    personality_prompt: str
    is_active: bool
    total_decisions: int
    last_decision_at: Optional[datetime]
    created_at: datetime
    last_processed_tweet_at: Optional[datetime] = None


class AgentThought(BaseModel):
    """Internal thought representation for agent state tracking"""

    agent_id: UUID
    step_number: int
    thought_type: AgentThoughtType
    content: str


class ThoughtInfo(BaseModel):
    """Individual thought in decision process"""

    thought_id: UUID
    step_number: int
    thought_type: AgentThoughtType
    content: str
    created_at: datetime


class DecisionInfo(BaseModel):
    """Agent decision information"""

    decision_id: UUID
    agent_id: UUID
    trigger_type: AgentDecisionTrigger
    trigger_tweet_id: Optional[str]
    action: AgentAction
    ticker: Optional[str]
    quantity: Optional[int]
    reasoning: Optional[str]
    order_id: Optional[UUID]
    executed: bool
    created_at: datetime


class DecisionDetail(DecisionInfo):
    """Decision with full thought trail"""

    agent_name: str
    thoughts: List[ThoughtInfo]


class MemoryInfo(BaseModel):
    """Agent memory information"""

    memory_id: UUID
    memory_type: AgentMemoryType
    content: str
    token_count: int
    created_at: datetime


class AgentMemoryState(BaseModel):
    """Current memory state of an agent"""

    agent_id: UUID
    working_memory: Optional[MemoryInfo]
    compressed_memories: List[MemoryInfo]
    total_tokens: int


class AgentStats(BaseModel):
    """Agent performance statistics"""

    agent_id: UUID
    name: str
    llm_model: LLMModel
    is_active: bool
    total_decisions: int
    last_decision_at: Optional[datetime]
    action_breakdown: Dict[str, int]
    trade_decisions: int
    executed_trades: int
    execution_rate: float


class AgentLeaderboardEntry(BaseModel):
    """Agent entry for the leaderboard"""

    agent_id: UUID
    name: str
    trader_id: UUID
    llm_model: LLMModel
    is_active: bool
    balance_in_cents: int
    total_assets_value_in_cents: int  # Balance + positions value
    total_trades_executed: int
    total_decisions: int
    profit_loss_in_cents: int  # Current balance - initial balance
    created_at: datetime
    last_decision_at: Optional[datetime]


class AgentLeaderboardResponse(BaseModel):
    """Response for agent leaderboard"""

    agents: List[AgentLeaderboardEntry]
    total: int


class AgentListResponse(BaseModel):
    """List of agents"""

    agents: List[Agent]
    total: int


class DecisionListResponse(BaseModel):
    """List of decisions"""

    decisions: List[DecisionInfo]
    total: int
    offset: int
    limit: int


# Event models for real-time streaming
class AgentThoughtEvent(BaseModel):
    """Real-time thought event"""

    event_type: str = "thought"
    agent_id: UUID
    agent_name: str
    decision_id: UUID
    thought: ThoughtInfo
    timestamp: datetime


class AgentDecisionEvent(BaseModel):
    """Real-time decision event"""

    event_type: str = "decision"
    agent_id: UUID
    agent_name: str
    decision: DecisionDetail
    timestamp: datetime


class AgentStatusEvent(BaseModel):
    """Agent status change event"""

    event_type: str = "status"
    agent_id: UUID
    agent_name: str
    status: str  # "thinking", "executing", "resting", "idle"
    timestamp: datetime
