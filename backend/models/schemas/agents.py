"""
Pydantic schemas for AI agents
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from enums import (
    AgentAction,
    AgentDecisionTrigger,
    AgentMemoryType,
    AgentThoughtType,
    AgentToolName,
    LLMModel,
)


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


class ThoughtInfo(BaseModel):
    """Agent thought information for API responses"""

    thought_id: UUID
    agent_id: UUID
    step_number: int
    thought_type: AgentThoughtType
    content: str
    tool_name: Optional[AgentToolName]
    tool_args: Optional[str]
    tool_result: Optional[str]
    created_at: datetime


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
    total_thoughts: int
    thought_breakdown: Dict[str, int]
    last_activity_at: Optional[datetime]


class AgentLeaderboardEntry(BaseModel):
    """Agent entry for the leaderboard"""

    agent_id: UUID
    name: str
    trader_id: UUID
    llm_model: LLMModel
    is_active: bool
    initial_balance_in_cents: int
    balance_in_cents: int
    total_assets_value_in_cents: int  # Balance + positions value
    total_trades_executed: int
    total_decisions: int
    profit_loss_in_cents: int  # (Cash + positions value) - initial balance
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


class ThoughtListResponse(BaseModel):
    """List of agent thoughts"""

    thoughts: List[ThoughtInfo]
    total: int
    offset: int
    limit: int


class AgentStatusEvent(BaseModel):
    """Agent status change event"""

    event_type: str = "status"
    agent_id: UUID
    agent_name: str
    status: str  # "thinking", "executing", "resting", "idle"
    timestamp: datetime


# Activity models for unified timeline
class ActivityItem(BaseModel):
    """Base class for activity items"""

    activity_type: str
    created_at: datetime
    agent_id: UUID


class ThoughtActivity(ActivityItem):
    """Thought activity item"""

    activity_type: Literal["thought"] = "thought"
    thought_id: UUID
    step_number: int
    thought_type: AgentThoughtType
    content: str


class DecisionActivity(ActivityItem):
    """Decision activity item"""

    activity_type: Literal["decision"] = "decision"
    decision_id: UUID
    trigger_type: AgentDecisionTrigger
    trigger_tweet_id: Optional[str]
    action: AgentAction
    ticker: Optional[str]
    quantity: Optional[int]
    reasoning: Optional[str]
    order_id: Optional[UUID]
    executed: bool


class AgentActivityResponse(BaseModel):
    """Response for agent activity endpoint"""

    activities: List[Union[ThoughtActivity, DecisionActivity]]
    total: int
    offset: int
    limit: int
