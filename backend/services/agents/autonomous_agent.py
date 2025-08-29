"""
Autonomous trading agent using LangGraph for state management
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from enums import AgentAction, AgentDecisionTrigger, AgentThoughtType
from models.schemas.agents import Agent, AgentThought
from models.schemas.tweet_feed import TweetForAgent
from services.agents.agent_tools import (
    get_trading_tools,
    get_utility_tools,
    get_x_data_tools,
)
from services.agents.db_utils import (
    get_agent_safe,
    get_tweets_safe,
    record_decision_safe,
    save_orphan_thoughts_safe,
    update_last_processed_tweet_safe,
)
from services.agents.memory_manager import MemoryManager
from services.agents.system_prompt import build_system_prompt
from services.agents.utils import create_llm


class AgentState(BaseModel):
    """State for the agent graph"""

    agent_id: UUID
    messages: List[BaseMessage] = Field(default_factory=list)
    thoughts: List[AgentThought] = Field(default_factory=list)  # For database storage
    pending_tweets: List[TweetForAgent] = Field(default_factory=list)
    pending_tool_calls: List = Field(default_factory=list)  # Tool calls from LLM
    memory_context: str = ""
    cycle_count: int = 0
    is_active: bool = True
    error_context: str = ""
    last_decision_id: Optional[UUID] = None  # Track current decision


class AutonomousAgent:
    """Autonomous agent that makes trading decisions"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.llm = create_llm(self.agent.llm_model, self.agent.temperature)
        self.memory_manager = MemoryManager(
            agent=agent,
        )
        self.running = True
        self.tools_list = self._get_all_tools()  # List of StructuredTools for LLM
        self.tools_map = self._create_tool_registry()  # Map for execution
        self.graph = None  # Will hold the compiled graph

    def _get_all_tools(self) -> List:
        """Get all available tools as StructuredTool objects"""
        trading_tools = get_trading_tools()
        x_data_tools = get_x_data_tools()
        utility_tools = get_utility_tools()

        return trading_tools + x_data_tools + utility_tools

    def _create_tool_registry(self) -> Dict[str, Any]:
        """Create registry mapping tool names to coroutines"""
        registry = {}
        for tool in self.tools_list:
            registry[tool.name] = tool.coroutine
        return registry

    def _create_graph(self) -> StateGraph:
        """Create the agent workflow graph"""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("check_active", self.check_active_node)
        graph.add_node("think", self.think_node)
        graph.add_node("execute_tools", self.execute_tools_node)
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
                "save": "save_thoughts",
            },
        )

        graph.add_edge("execute_tools", "save_thoughts")
        graph.add_edge("save_thoughts", "check_active")

        return graph

    async def check_active_node(self, state: AgentState) -> AgentState:
        """Check if agent is still active"""
        # Use isolated database operation
        agent = await get_agent_safe(self.agent.agent_id)
        state.is_active = agent.is_active

        # Increment cycle count
        state.cycle_count += 1

        # Check for new tweets every 5 cycles
        if state.cycle_count % 5 == 0:
            # Use isolated database operation for tweets
            state.pending_tweets = await get_tweets_safe(
                after_timestamp=self.agent.last_processed_tweet_at,
                limit=100,
            )

            if state.pending_tweets:
                # Update last processed timestamp in isolated transaction
                latest_timestamp = max(t.fetched_at for t in state.pending_tweets)
                await update_last_processed_tweet_safe(
                    self.agent.agent_id, latest_timestamp
                )

        return state

    async def think_node(self, state: AgentState) -> AgentState:
        """Main thinking/decision node using native tool calling"""
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

        # Bind tools to the LLM for native tool calling
        llm_with_tools = self.llm.bind_tools(self.tools_list)

        # Build messages - use existing messages or start fresh
        if not state.messages:
            # Build complete system prompt from personality
            system_prompt = build_system_prompt(self.agent.personality_prompt)
            state.messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context),
            ]
        else:
            # Add new context as a message
            state.messages.append(HumanMessage(content=context))

        # Get response with potential tool calls
        response = await llm_with_tools.ainvoke(state.messages)

        # Store the AI message in state
        state.messages.append(response)

        # Extract tool calls if any
        if hasattr(response, "tool_calls") and response.tool_calls:
            state.pending_tool_calls = response.tool_calls
        else:
            state.pending_tool_calls = []

        # Store reasoning if present
        if response.content:
            # Create thought for database storage
            thought = AgentThought(
                agent_id=self.agent.agent_id,
                step_number=state.cycle_count,
                thought_type=AgentThoughtType.THINKING,
                content=response.content[:2000],  # Limit to field size
            )
            state.thoughts.append(thought)

        return state

    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute native OpenAI tool calls and add results as ToolMessages"""
        if not state.pending_tool_calls:
            return state

        for tool_call in state.pending_tool_calls:
            tool_name = tool_call["name"]
            tool_id = tool_call["id"]
            arguments = tool_call["args"]

            # Add trader_id for tools that need it
            if tool_name in ["buy_stock", "sell_stock", "check_portfolio"]:
                arguments["trader_id"] = str(self.agent.trader_id)

            try:
                if tool_name not in self.tools_map:
                    raise ValueError(f"Unknown tool: {tool_name}")

                # Execute the tool
                result = await self.tools_map[tool_name](**arguments)

                # Convert result to dict/string for ToolMessage
                if hasattr(result, "model_dump"):
                    result_str = json.dumps(result.model_dump())
                elif hasattr(result, "dict"):
                    result_str = json.dumps(result.dict())
                elif isinstance(result, dict):
                    result_str = json.dumps(result)
                else:
                    result_str = str(result)

                # Add tool result as ToolMessage
                tool_message = ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id,
                )
                state.messages.append(tool_message)

                # Record trading decisions with repository
                if tool_name in ["buy_stock", "sell_stock"]:
                    # Parse result to check if successful
                    result_dict = (
                        json.loads(result_str)
                        if isinstance(result_str, str)
                        else result_str
                    )
                    action = (
                        AgentAction.BUY
                        if tool_name == "buy_stock"
                        else AgentAction.SELL
                    )
                    success = (
                        result_dict.get("success", False)
                        if isinstance(result_dict, dict)
                        else False
                    )
                    order_id = (
                        result_dict.get("order_id")
                        if success and isinstance(result_dict, dict)
                        else None
                    )

                    # Determine trigger type
                    trigger_type = (
                        AgentDecisionTrigger.TWEET
                        if state.pending_tweets
                        else AgentDecisionTrigger.AUTONOMOUS
                    )
                    trigger_tweet_id = (
                        state.pending_tweets[0].tweet_id
                        if state.pending_tweets
                        else None
                    )

                    # Extract reasoning from recent messages
                    reasoning = ""
                    for msg in reversed(state.messages):
                        if isinstance(msg, AIMessage) and msg.content:
                            reasoning = msg.content[:500]
                            break

                    # Use isolated database operation for recording decision
                    decision_id = await record_decision_safe(
                        agent_id=self.agent.agent_id,
                        trigger_type=trigger_type,
                        action=action,
                        thoughts=[
                            (t.thought_type, t.content) for t in state.thoughts[-5:]
                        ],
                        ticker=arguments.get("ticker"),
                        quantity=arguments.get("quantity"),
                        reasoning=reasoning,
                        trigger_tweet_id=trigger_tweet_id,
                        order_id=UUID(order_id) if order_id else None,
                        executed=success,
                    )
                    state.last_decision_id = decision_id

            except Exception as e:
                # Create error message as ToolMessage
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_id,
                )
                state.messages.append(error_message)

                # Log error as thought
                thought = AgentThought(
                    agent_id=self.agent.agent_id,
                    step_number=state.cycle_count,
                    thought_type=AgentThoughtType.DECIDING,
                    content=f"Error with {tool_name}: {str(e)[:500]}",
                )
                state.thoughts.append(thought)

        # Clear pending tool calls after processing
        state.pending_tool_calls = []

        return state

    async def save_thoughts_node(self, state: AgentState) -> AgentState:
        """Save thoughts to database using repository and compress memory if needed"""
        if state.thoughts:
            # If we have a current decision, thoughts are already saved with it
            if not state.last_decision_id:
                # Save orphan thoughts using isolated database operation
                await save_orphan_thoughts_safe(
                    agent_id=self.agent.agent_id,
                    thoughts=state.thoughts[-10:]  # Save last 10 thoughts
                )

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

    def route_from_think(self, state: AgentState) -> str :
        """Route from think node based on whether there are tool calls"""
        if state.pending_tool_calls:
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
