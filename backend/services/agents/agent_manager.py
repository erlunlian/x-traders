"""
Agent manager service that orchestrates all AI agents
"""

import asyncio
from typing import Any, Dict, List
from uuid import UUID

from database import async_session
from database.repositories import AgentRepository
from models.schemas.agents import Agent
from services.agents.autonomous_agent import AutonomousAgent
from services.agents.db_utils import get_agent_or_none_safe, get_active_agents_safe


class AgentManager:
    """Manages all running AI agents"""

    def __init__(self) -> None:
        self.agents: Dict[UUID, AutonomousAgent] = {}
        self.running_tasks: Dict[UUID, asyncio.Task] = {}
        self.running = False

    async def start(self) -> None:
        """Start the agent manager and all active agents"""
        self.running = True

        # Load all active agents from database
        active_agents = await get_active_agents_safe()

        print(f"Starting {len(active_agents)} active agents...")

        # Start each agent
        for agent in active_agents:
            await self.start_agent(agent)

        print(f"All agents started. Managing {len(self.agents)} agents.")

    async def stop(self) -> None:
        """Stop all agents and the manager"""
        self.running = False

        # Stop all agents
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)

        print("All agents stopped.")

    async def start_agent(self, agent: Agent) -> None:
        """Start a single agent"""
        if agent.agent_id in self.agents:
            print(f"Agent {agent.name} already running")
            return

        # Create autonomous agent
        autonomous_agent = AutonomousAgent(agent)
        self.agents[agent.agent_id] = autonomous_agent

        # Start the agent's run_forever task
        task = asyncio.create_task(
            autonomous_agent.run_forever(), name=f"agent_{agent.name}"
        )
        self.running_tasks[agent.agent_id] = task

        print(f"Started agent: {agent.name} (ID: {agent.agent_id})")

    async def stop_agent(self, agent_id: UUID) -> None:
        """Stop a single agent"""
        if agent_id not in self.agents:
            return

        # Stop the agent
        agent = self.agents[agent_id]
        agent.stop()

        # Cancel the task
        if agent_id in self.running_tasks:
            task = self.running_tasks[agent_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.running_tasks[agent_id]

        del self.agents[agent_id]
        print(f"Stopped agent ID: {agent_id}")

    async def restart_agent(self, agent_id: UUID) -> None:
        """Restart an agent"""
        # Stop if running
        await self.stop_agent(agent_id)

        # Reload from database using safe method
        agent = await get_agent_or_none_safe(agent_id)

        if agent and agent.is_active:
            await self.start_agent(agent)

    async def get_agent_status(self, agent_id: UUID) -> Dict[str, Any]:
        """Get status of a specific agent"""
        if agent_id not in self.agents:
            return {"status": "not_running"}

        agent = self.agents[agent_id]
        task = self.running_tasks.get(agent_id)

        return {
            "status": "running" if agent.running else "stopped",
            "task_done": task.done() if task else None,
            "agent_name": agent.agent.name,
        }

    async def get_all_agent_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all agents"""
        statuses = []

        # Get all agents from database
        async with async_session() as session:
            repo = AgentRepository(session)
            all_agents = await repo.list_agents()

        for agent in all_agents:
            status = await self.get_agent_status(agent.agent_id)
            status["agent_id"] = agent.agent_id
            status["name"] = agent.name
            status["is_active"] = agent.is_active
            statuses.append(status)

        return statuses

    async def monitor_agents(self) -> None:
        """Monitor agent health and restart if needed"""
        while self.running:
            try:
                # Check each running task
                for agent_id, task in list(self.running_tasks.items()):
                    if task.done():
                        # Task finished unexpectedly
                        try:
                            # Get the exception if any
                            task.result()
                        except Exception as e:
                            print(f"Agent {agent_id} crashed: {e}")

                        # Restart the agent
                        print(f"Restarting agent {agent_id}...")
                        await self.restart_agent(agent_id)

                # Check for new agents every minute
                await asyncio.sleep(60)

                # Load any newly activated agents
                active_agents = await get_active_agents_safe()

                for agent in active_agents:
                    if agent.agent_id not in self.agents:
                        print(f"Found new active agent: {agent.name}")
                        await self.start_agent(agent)

            except Exception as e:
                print(f"Agent monitor error: {e}")
                await asyncio.sleep(10)


# Global agent manager instance
agent_manager = AgentManager()
