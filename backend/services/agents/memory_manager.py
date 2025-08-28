"""
Memory management for AI agents with compression
"""

from typing import List, Optional
from uuid import UUID

import tiktoken
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from database import async_session
from database.repositories import AgentRepository
from enums import AgentMemoryType, AgentThoughtType, LLMModel
from models.schemas.agents import AgentMemoryState, MemoryInfo
from models.schemas.model_config import ModelProvider, ModelRegistry


class MemoryManager:
    """Manages agent memory with compression at 80% threshold"""

    def __init__(self, agent_id: UUID, llm_model: LLMModel):
        self.agent_id = agent_id
        self.llm_model = llm_model
        self.model_config = ModelRegistry.get(llm_model)
        self.compression_threshold = self.model_config.max_context_tokens
        self.llm = self._create_llm()
        self.encoder = self._get_encoder()

    def _create_llm(self):
        """Create LLM for memory compression"""
        if self.model_config.provider == ModelProvider.OPENAI:
            return ChatOpenAI(
                model=self.llm_model.value,
                temperature=0.3,  # Lower temp for compression
            )
        elif self.model_config.provider == ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=self.llm_model.value,
                temperature=0.3,
            )
        else:
            # xAI/Grok
            return ChatOpenAI(
                model=self.llm_model.value,
                temperature=0.3,
                base_url="https://api.x.ai/v1",
            )

    def _get_encoder(self):
        """Get appropriate tokenizer for the model"""
        if self.model_config.provider == ModelProvider.OPENAI:
            # Use cl100k_base for GPT-4/GPT-5 models
            return tiktoken.get_encoding("cl100k_base")
        elif self.model_config.provider == ModelProvider.ANTHROPIC:
            # Claude uses a similar tokenizer, approximate with cl100k_base
            return tiktoken.get_encoding("cl100k_base")
        else:
            # xAI/Grok also similar to GPT
            return tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))

    async def get_memory_state(self) -> AgentMemoryState:
        """Get current memory state"""
        async with async_session() as session:
            repo = AgentRepository(session)
            return await repo.get_agent_memory(self.agent_id)

    async def should_compress(self) -> bool:
        """Check if memory should be compressed"""
        state = await self.get_memory_state()
        return state.total_tokens > self.compression_threshold

    async def add_to_memory(self, thoughts: List[tuple[AgentThoughtType, str]]):
        """Add new thoughts to working memory"""
        # Format thoughts as structured memory
        memory_entries = []
        for thought_type, content in thoughts:
            memory_entries.append(f"[{thought_type.value}] {content}")

        new_content = "\n".join(memory_entries)

        # Get current memory
        state = await self.get_memory_state()

        # Append to working memory
        if state.working_memory:
            updated_content = f"{state.working_memory.content}\n\n{new_content}"
        else:
            updated_content = new_content

        # Count tokens
        token_count = self.count_tokens(updated_content)

        # Save to database
        async with async_session() as session:
            repo = AgentRepository(session)
            await repo.save_memory_without_commit(
                agent_id=self.agent_id,
                memory_type=AgentMemoryType.WORKING,
                content=updated_content,
                token_count=token_count,
            )
            await session.commit()

    async def compress_memory(self):
        """Compress working memory into compressed memory"""
        state = await self.get_memory_state()

        if not state.working_memory:
            return

        # Prepare compression prompt
        compression_prompt = f"""Compress the following memory into key insights and important events.
Focus on:
1. Successful trades and their reasoning
2. Failed trades and lessons learned
3. Market patterns observed
4. Important tweet signals
5. Overall strategy evolution

Working Memory:
{state.working_memory.content}

Previous Compressed Memories (for context):
{self._format_compressed_memories(state.compressed_memories)}

Create a concise summary that preserves critical trading insights and patterns."""

        messages = [
            SystemMessage(
                content="You are a memory compression system. Extract and preserve key insights."
            ),
            HumanMessage(content=compression_prompt),
        ]

        # Compress using LLM
        response = await self.llm.ainvoke(messages)
        compressed_content = response.content
        compressed_tokens = self.count_tokens(compressed_content)

        # Save compressed memory and clear working memory
        async with async_session() as session:
            repo = AgentRepository(session)

            # Save new compressed memory
            await repo.save_memory_without_commit(
                agent_id=self.agent_id,
                memory_type=AgentMemoryType.COMPRESSED,
                content=compressed_content,
                token_count=compressed_tokens,
            )

            # Clear working memory by saving empty
            await repo.save_memory_without_commit(
                agent_id=self.agent_id,
                memory_type=AgentMemoryType.WORKING,
                content="",
                token_count=0,
            )

            # Clean up old compressed memories if too many
            await repo.cleanup_old_memories_without_commit(
                agent_id=self.agent_id,
                keep_last_n=5,  # Keep last 5 compressed memories
            )

            await session.commit()

    def _format_compressed_memories(self, memories: List[MemoryInfo]) -> str:
        """Format compressed memories for context"""
        if not memories:
            return "No previous compressed memories."

        formatted = []
        for memory in memories[:3]:  # Only use last 3 for context
            formatted.append(f"[{memory.created_at.isoformat()}]\n{memory.content}")

        return "\n\n".join(formatted)

    async def get_formatted_memory_for_prompt(self) -> str:
        """Get formatted memory for including in agent prompts"""
        state = await self.get_memory_state()

        sections = []

        # Add working memory
        if state.working_memory and state.working_memory.content:
            sections.append(f"Recent Activity:\n{state.working_memory.content}")

        # Add compressed memories (most recent first)
        if state.compressed_memories:
            compressed_summary = "Historical Insights:\n"
            for memory in state.compressed_memories[:2]:  # Use top 2
                compressed_summary += f"\n{memory.content}"
            sections.append(compressed_summary)

        return "\n\n---\n\n".join(sections) if sections else "No memory available."

    async def extract_insights(self) -> Optional[str]:
        """Extract trading insights from all memories"""
        state = await self.get_memory_state()

        if not state.working_memory and not state.compressed_memories:
            return None

        insight_prompt = f"""Analyze the agent's memory and extract key trading insights:

{await self.get_formatted_memory_for_prompt()}

Extract:
1. Most profitable patterns
2. Common mistakes to avoid
3. Effective trading strategies
4. Important market signals

Provide actionable insights for future trading decisions."""

        messages = [
            SystemMessage(
                content="You are analyzing an agent's trading memory to extract insights."
            ),
            HumanMessage(content=insight_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        insights = str(response.content)

        # Save as INSIGHTS type memory
        async with async_session() as session:
            repo = AgentRepository(session)
            await repo.save_memory_without_commit(
                agent_id=self.agent_id,
                memory_type=AgentMemoryType.INSIGHTS,
                content=insights,
                token_count=self.count_tokens(insights),
            )
            await session.commit()

        return insights
