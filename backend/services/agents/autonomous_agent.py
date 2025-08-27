"""
Autonomous trading agent using LangGraph for state management
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from database import async_session
from database.repositories import AgentRepository, XDataRepository
from enums import AgentAction, AgentDecisionTrigger, AgentThoughtType
from models.schemas.agents import Agent, AgentThought
from models.schemas.tweet_feed import TweetForAgent
from services.agents.agent_tools import get_trading_tools, get_x_data_tools
from services.agents.memory_manager import MemoryManager


# Structured output models for LLM responses
class ToolCall(BaseModel):
    """Represents a tool call from the agent"""

    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ThinkingResponse(BaseModel):
    """Agent's response from the thinking node"""

    action: str = Field(description="One of: execute_tools, rest, continue")
    reasoning: str = Field(description="Current thinking process")
    tool_calls: List[ToolCall] = Field(
        default_factory=list, description="Tools to execute if action is execute_tools"
    )
    rest_minutes: int = Field(
        default=5, description="Minutes to rest if action is rest"
    )


class AgentState(BaseModel):
    """State for the agent graph"""

    agent_id: UUID
    current_thought: Optional[str] = None
    thoughts: List[AgentThought] = Field(default_factory=list)
    pending_tweets: List[TweetForAgent] = Field(default_factory=list)
    memory_context: str = ""
    tool_results: Dict[str, Any] = Field(default_factory=dict)
    should_rest: bool = False
    rest_duration_minutes: int = 5
    cycle_count: int = 0
    is_active: bool = True
    error_context: str = ""
    last_decision_id: Optional[UUID] = None  # Track current decision


class AutonomousAgent:
    """Autonomous agent that makes trading decisions"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.llm = self._create_llm()
        self.memory_manager = MemoryManager(
            agent_id=agent.agent_id,
            llm_model=agent.llm_model,
        )
        self.running = True
        self.tools = self._create_tool_registry()
        self.graph = None  # Will hold the compiled graph

    def _create_llm(self):
        """Create the appropriate LLM based on configuration"""
        model_name = self.agent.llm_model.value

        if model_name.startswith("gpt"):
            return AzureChatOpenAI(
                model=model_name,
                temperature=float(self.agent.temperature),
            )
        elif model_name.startswith("claude"):
            return ChatAnthropic(
                model=model_name,
                temperature=float(self.agent.temperature),
            )
        elif model_name.startswith("grok"):
            # Grok uses OpenAI-compatible API
            return ChatOpenAI(
                model=model_name,
                temperature=float(self.agent.temperature),
                base_url="https://api.x.ai/v1",  # X.AI's API endpoint
            )
        else:
            raise ValueError(f"Unknown model: {model_name}")

    def _create_tool_registry(self) -> Dict[str, Any]:
        """Create registry of available tools from agent_tools.py"""
        # Get all tools from agent_tools
        trading_tools = get_trading_tools()
        x_data_tools = get_x_data_tools()

        # Build a dictionary mapping tool names to functions
        registry = {}

        for tool in trading_tools + x_data_tools:
            # Extract the async function from the StructuredTool
            registry[tool.name] = tool.coroutine

        return registry

    def _create_graph(self) -> StateGraph:
        """Create the agent workflow graph"""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("check_active", self.check_active_node)
        graph.add_node("think", self.think_node)
        graph.add_node("execute_tools", self.execute_tools_node)
        graph.add_node("rest", self.rest_node)
        graph.add_node("save_thoughts", self.save_thoughts_node)

        # Set entry point
        graph.set_entry_point("check_active")

        # Add edges
        graph.add_conditional_edges(
            "check_active",
            self.route_from_check_active,
            {
                "continue": "think",
                END: END,
            },
        )

        graph.add_conditional_edges(
            "think",
            self.route_from_think,
            {
                "execute": "execute_tools",
                "rest": "rest",
                "save": "save_thoughts",
            },
        )

        graph.add_edge("execute_tools", "save_thoughts")
        graph.add_edge("rest", "save_thoughts")
        graph.add_edge("save_thoughts", "check_active")

        return graph

    async def check_active_node(self, state: AgentState) -> AgentState:
        """Check if agent is still active"""
        async with async_session() as session:
            repo = AgentRepository(session)
            agent = await repo.get_agent(self.agent.agent_id)
            state.is_active = agent.is_active

        # Increment cycle count
        state.cycle_count += 1

        # Check for new tweets every 5 cycles
        if state.cycle_count % 5 == 0:
            async with async_session() as session:
                x_repo = XDataRepository(session)
                # Use the new method that returns properly typed TweetForAgent models
                state.pending_tweets = await x_repo.get_tweets_for_agent(
                    after_timestamp=self.agent.last_processed_tweet_at,
                    limit=100,
                )

                if state.pending_tweets:
                    # Update last processed timestamp
                    latest_timestamp = max(t.fetched_at for t in state.pending_tweets)
                    agent_repo = AgentRepository(session)
                    await agent_repo.update_last_processed_tweet_without_commit(
                        self.agent.agent_id, latest_timestamp
                    )
                    await session.commit()

        return state

    async def think_node(self, state: AgentState) -> AgentState:
        """Main thinking/decision node"""
        # Get memory context
        state.memory_context = (
            await self.memory_manager.get_formatted_memory_for_prompt()
        )

        # Build context
        context = f"""
Memory context: {state.memory_context}
Current timestamp: {datetime.now(timezone.utc).isoformat()}
Cycle: {state.cycle_count}
"""

        if state.pending_tweets:
            context += f"\nNew tweets detected: {len(state.pending_tweets)} tweets"
            # Show first few tweets
            for tweet in state.pending_tweets[:3]:
                context += f"\n- @{tweet.author_username}: {tweet.text[:100]}..."

        if state.error_context:
            context += f"\n\nPrevious errors:\n{state.error_context}"

        # Get tool descriptions
        trading_tools = get_trading_tools()
        x_data_tools = get_x_data_tools()

        tools_desc = "Available tools:\n"
        for tool in trading_tools + x_data_tools:
            tools_desc += f"- {tool.name}: {tool.description}\n"

        # Ask LLM what to do using structured output
        llm_with_structure = self.llm.with_structured_output(ThinkingResponse)

        messages = [
            SystemMessage(content=self.agent.system_prompt),
            HumanMessage(
                content=f"""
{context}

{tools_desc}

What would you like to do? You can:
1. Call one or more tools (action: "execute_tools")
2. Rest for a while (action: "rest")
3. Just think and continue (action: "continue")

Decide your next action.
"""
            ),
        ]

        response = await llm_with_structure.ainvoke(messages)

        # Store the response
        state.current_thought = response.reasoning

        if response.action == "rest":
            state.should_rest = True
            state.rest_duration_minutes = response.rest_minutes
        elif response.action == "execute_tools":
            state.tool_results = {"pending_calls": response.tool_calls}

        # Log thought
        thought = AgentThought(
            agent_id=self.agent.agent_id,
            step_number=len(state.thoughts),
            thought_type=AgentThoughtType.ANALYZING,
            content=state.current_thought,
        )
        state.thoughts.append(thought)

        return state

    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute tool calls"""
        pending_calls = state.tool_results.get("pending_calls", [])
        results = []
        errors = []

        for call in pending_calls:
            tool_name = call.tool
            arguments = call.arguments

            # Add trader_id for tools that need it
            if tool_name in ["buy_stock", "sell_stock", "check_portfolio"]:
                arguments["trader_id"] = str(self.agent.trader_id)

            if tool_name in self.tools:
                try:
                    result = await self.tools[tool_name](**arguments)

                    # Convert result to dict if needed
                    if hasattr(result, "model_dump"):
                        result = result.model_dump()
                    elif hasattr(result, "dict"):
                        result = result.dict()

                    results.append({"tool": tool_name, "result": result})

                    # Record trading decisions with repository
                    if tool_name in ["buy_stock", "sell_stock"]:
                        action = (
                            AgentAction.BUY
                            if tool_name == "buy_stock"
                            else AgentAction.SELL
                        )

                        # Determine if trade was successful
                        success = result.get("success", False)
                        order_id = result.get("order_id") if success else None

                        # Determine trigger type (from tweets or autonomous)
                        trigger_type = (
                            AgentDecisionTrigger.TWEET
                            if state.pending_tweets
                            else AgentDecisionTrigger.AUTONOMOUS
                        )

                        # Get first tweet ID if triggered by tweets
                        trigger_tweet_id = (
                            state.pending_tweets[0].tweet_id
                            if state.pending_tweets
                            and trigger_type == AgentDecisionTrigger.TWEET
                            else None
                        )

                        async with async_session() as session:
                            repo = AgentRepository(session)
                            decision = await repo.record_decision_without_commit(
                                agent_id=self.agent.agent_id,
                                trigger_type=trigger_type,
                                action=action,
                                thoughts=[
                                    (t.thought_type, t.content)
                                    for t in state.thoughts[-5:]
                                ],  # Last 5 thoughts
                                ticker=arguments.get("ticker"),
                                quantity=arguments.get("quantity"),
                                reasoning=state.current_thought,
                                trigger_tweet_id=trigger_tweet_id,
                                order_id=UUID(order_id) if order_id else None,
                                executed=success,
                            )
                            await session.commit()

                            # Store decision ID for reference
                            state.last_decision_id = decision.decision_id

                except Exception as e:
                    errors.append(f"{tool_name}: {str(e)}")
                    results.append({"tool": tool_name, "error": str(e)})
            else:
                errors.append(f"Unknown tool: {tool_name}")

        # Store results and errors
        state.tool_results = {"results": results}
        state.error_context = "\n".join(errors) if errors else ""

        # Log execution results as thoughts
        for result in results:
            thought = AgentThought(
                agent_id=self.agent.agent_id,
                step_number=len(state.thoughts),
                thought_type=AgentThoughtType.DECIDING,
                content=f"{result['tool']}: {json.dumps(result.get('result', result.get('error', {})))[:500]}",
            )
            state.thoughts.append(thought)

        # Clear pending tweets after processing
        state.pending_tweets = []

        return state

    async def rest_node(self, state: AgentState) -> AgentState:
        """Rest for a specified duration"""
        duration = state.rest_duration_minutes
        print(f"Agent {self.agent.name} resting for {duration} minutes...")

        thought = AgentThought(
            agent_id=self.agent.agent_id,
            step_number=len(state.thoughts),
            thought_type=AgentThoughtType.REFLECTING,
            content=f"Taking a break for {duration} minutes",
        )
        state.thoughts.append(thought)

        # Record REST decision
        async with async_session() as session:
            repo = AgentRepository(session)
            await repo.record_decision_without_commit(
                agent_id=self.agent.agent_id,
                trigger_type=AgentDecisionTrigger.AUTONOMOUS,
                action=AgentAction.REST,
                thoughts=[(t.thought_type, t.content) for t in state.thoughts[-3:]],
                reasoning=f"Decided to rest for {duration} minutes",
            )
            await session.commit()

        await asyncio.sleep(duration * 60)

        state.should_rest = False
        return state

    async def save_thoughts_node(self, state: AgentState) -> AgentState:
        """Save thoughts to database using repository and compress memory if needed"""
        if state.thoughts:
            # Save thoughts using repository method
            async with async_session() as session:
                repo = AgentRepository(session)

                # If we have a current decision, associate thoughts with it
                if state.last_decision_id:
                    # The thoughts are already saved with the decision
                    pass
                else:
                    # Save orphan thoughts (not associated with a decision)
                    for thought in state.thoughts[-10:]:  # Save last 10 thoughts
                        await repo.save_orphan_thought_without_commit(
                            agent_id=self.agent.agent_id,
                            thought_type=thought.thought_type,
                            content=thought.content,
                            step_number=thought.step_number,
                        )

                await session.commit()

            # Compress memory if needed
            if await self.memory_manager.should_compress():
                await self.memory_manager.compress_memory()

            # Keep only recent thoughts in state
            state.thoughts = state.thoughts[-5:]

        return state

    def route_from_check_active(self, state: AgentState) -> str:
        """Route from check_active node"""
        if not state.is_active:
            return END
        return "continue"

    def route_from_think(self, state: AgentState) -> str:
        """Route from think node"""
        if state.should_rest:
            return "rest"
        elif state.tool_results.get("pending_calls"):
            return "execute"
        else:
            return "save"

    async def run_forever(self):
        """Main execution loop"""
        print(f"Starting agent {self.agent.name}")

        # Create and compile the graph
        graph = self._create_graph()
        self.graph = graph.compile()

        # Initialize state
        state = AgentState(agent_id=self.agent.agent_id)

        try:
            while self.running:
                # Run one cycle through the graph
                result = await self.graph.ainvoke(state)

                # Update state for next iteration
                state = result

                # Check if we should stop
                if not state.is_active:
                    print(f"Agent {self.agent.name} stopping (is_active=False)")
                    break

                # Small delay between cycles
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Agent {self.agent.name} error: {e}")
            raise
        finally:
            print(f"Agent {self.agent.name} stopped")

    def stop(self):
        """Stop the agent"""
        self.running = False
