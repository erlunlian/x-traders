"""
Autonomous trading agent using LangGraph for state management
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from enums import AgentThoughtType, AgentToolName
from models.schemas.agents import Agent, ThoughtInfo
from models.schemas.tweet_feed import TweetForAgent
from services.agents.agent_tools import get_trading_tools, get_utility_tools, get_x_data_tools
from services.agents.db_utils import (
    create_thought_safe,
    get_agent_safe,
    get_tweets_safe,
    update_last_processed_tweet_safe,
)
from services.agents.memory_manager import MemoryManager
from services.agents.system_prompt import build_system_prompt
from services.agents.utils import create_llm


class AgentState(BaseModel):
    """State for the agent graph"""

    agent_id: UUID
    messages: List[BaseMessage] = Field(default_factory=list)
    thoughts: List[ThoughtInfo] = Field(default_factory=list)  # For database storage
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
        self.trader_id = str(self.agent.trader_id)  # Store trader_id as string for tools
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
        # Pass trader_id to get wrapped tools that don't require trader_id parameter
        trading_tools = get_trading_tools(trader_id=self.trader_id)
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
                "think_again": "think",  # Loop back to think if no tool calls
            },
        )

        graph.add_edge("execute_tools", "check_active")

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
                await update_last_processed_tweet_safe(self.agent.agent_id, latest_timestamp)

        return state

    async def append_think_context_to_state_messages(self, state: AgentState) -> str:
        """Build the context for the think node"""
        # Get memory context
        state.memory_context = await self.memory_manager.get_formatted_memory_for_prompt()

        # Build context
        context = f"""
Memory context: {state.memory_context}
Current timestamp: {datetime.now(timezone.utc).isoformat()}
Cycle: {state.cycle_count}
"""

        if state.pending_tweets:
            context += f"\nNew tweets detected: {len(state.pending_tweets)} tweets"
            # Show first few tweets
            for tweet in state.pending_tweets:
                context += f"\n- @{tweet.author_username}: {tweet.text}"

        if state.error_context:
            context += f"\n\nPrevious errors:\n{state.error_context}"

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

    async def think_node(self, state: AgentState) -> AgentState:
        """Main thinking/decision node using native tool calling"""
        # set context for think node
        await self.append_think_context_to_state_messages(state)

        # Bind tools to the LLM for native tool calling
        llm_with_tools = self.llm.bind_tools(self.tools_list)

        # Get response with potential tool calls
        response = await llm_with_tools.ainvoke(state.messages)

        # Store the full AI response in state (includes tool calls)
        state.messages.append(response)

        # Extract tool calls if any
        state.pending_tool_calls = (
            response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []
        )

        # Store reasoning if present
        if response.content:
            thought_info = await create_thought_safe(
                agent_id=state.agent_id,
                step_number=state.cycle_count,
                thought_type=AgentThoughtType.THINKING,
                content=response.content,
                tool_name=None,  # No tool for thinking thoughts
                tool_args=None,  # No tool args
                tool_result=None,  # No tool result
            )
            state.thoughts.append(thought_info)

        return state

    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute native OpenAI tool calls and add results as ToolMessages"""
        if not state.pending_tool_calls:
            return state

        for tool_call in state.pending_tool_calls:
            tool_name = tool_call["name"]
            tool_id = tool_call["id"]
            arguments = tool_call["args"]

            try:
                if tool_name not in self.tools_map:
                    raise ValueError(f"Unknown tool: {tool_name}")

                # Execute the tool
                result = await self.tools_map[tool_name](**arguments)

                # Convert result to dict/string for ToolMessage
                if hasattr(result, "model_dump"):
                    result_str = json.dumps(result.model_dump(), default=str)
                elif hasattr(result, "dict"):
                    result_str = json.dumps(result.dict(), default=str)
                elif isinstance(result, dict):
                    result_str = json.dumps(result, default=str)
                else:
                    result_str = str(result)

                # Add tool result as ToolMessage
                tool_message = ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id,
                )
                state.messages.append(tool_message)

                # Record all tool calls as thoughts
                tool_thought = await create_thought_safe(
                    agent_id=self.agent.agent_id,
                    step_number=state.cycle_count,
                    thought_type=AgentThoughtType.TOOL_CALL,
                    content="",
                    tool_name=AgentToolName(tool_name),
                    tool_args=json.dumps(arguments, default=str),
                    tool_result=result_str,
                )
                state.thoughts.append(tool_thought)

            except Exception as e:
                # Create error message as ToolMessage
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_id,
                )
                state.messages.append(error_message)

                # Log error as thought
                error_thought = await create_thought_safe(
                    agent_id=self.agent.agent_id,
                    step_number=state.cycle_count,
                    thought_type=AgentThoughtType.ERROR,
                    content=f"Error with {tool_name}: {str(e)}",
                    tool_name=AgentToolName(tool_name),
                    tool_args=json.dumps(arguments, default=str),
                    tool_result=f"Error with {tool_name}: {str(e)}",
                )
                state.thoughts.append(error_thought)

        # Clear pending tool calls after processing
        state.pending_tool_calls = []

        return state

    def route_from_check_active(self, state: AgentState) -> str:
        """Route from check_active node"""
        if not state.is_active:
            return END
        return "continue"

    def route_from_think(self, state: AgentState) -> str:
        """Route from think node based on whether there are tool calls"""
        # TODO add check to compact memory if it reaches 80% of max tokens for the agent's model
        if state.pending_tool_calls:
            return "execute"
        else:
            return "think_again"  # Loop back to think

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
