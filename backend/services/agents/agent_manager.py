"""
Agent manager service that orchestrates all AI agents
"""

import asyncio
import traceback
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, List
from uuid import UUID

from database import async_session, get_db_transaction
from database.repositories import AgentRepository, SettingsRepository
from models.schemas.agents import Agent
from services.agents.autonomous_agent import AutonomousAgent
from services.agents.db_utils import get_active_agents_safe, get_agent_or_none_safe


class AgentManager:
    """Manages all running AI agents"""

    def __init__(self) -> None:
        self.agents: Dict[UUID, AutonomousAgent] = {}
        self.running_tasks: Dict[UUID, asyncio.Task] = {}
        self.running = False
        # In-memory error buffers
        self.agent_errors: Dict[UUID, Deque[Dict[str, Any]]] = {}
        self.monitor_errors: Deque[Dict[str, Any]] = deque(maxlen=200)
        # Global pause state (e.g., due to LLM 429)
        self.globally_paused: bool = False
        self.global_pause_until: datetime | None = None
        self.global_pause_reason: str | None = None
        self._resume_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the agent manager and all active agents"""
        self.running = True

    def _record_agent_error(self, agent_id: UUID, error: BaseException) -> None:
        """Record an agent crash/error into a bounded deque."""
        if agent_id not in self.agent_errors:
            self.agent_errors[agent_id] = deque(maxlen=100)
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": str(agent_id),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
        }
        self.agent_errors[agent_id].append(error_entry)

    def _record_monitor_error(self, error: BaseException) -> None:
        """Record a monitor loop error into a bounded deque."""
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
        }
        self.monitor_errors.append(error_entry)

    async def get_monitor_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent monitor loop errors (most recent last)."""
        if limit <= 0:
            return list(self.monitor_errors)
        return list(self.monitor_errors)[-limit:]

    async def get_all_agents_errors(self, limit_per_agent: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent errors for all agents as a flat list with agent_id included."""
        results: List[Dict[str, Any]] = []
        for _agent_id, buf in self.agent_errors.items():
            if limit_per_agent <= 0:
                slice_items = list(buf)
            else:
                slice_items = list(buf)[-limit_per_agent:]
            results.extend(slice_items)
        # Sort by timestamp ascending to be consistent (most recent last)
        results.sort(key=lambda e: e.get("timestamp", ""))
        return results

    async def stop(self) -> None:
        """Stop all agents and the manager"""
        self.running = False

        # Stop all agents
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)

        print("All agents stopped.")

    async def pause_all_for(self, seconds: int, reason: str) -> None:
        """Pause all agents for the specified number of seconds with a reason."""
        # Set state
        self.running = True  # Ensure monitor loop can run even while paused
        self.globally_paused = True
        self.global_pause_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        self.global_pause_reason = reason

        # Stop any running agents immediately
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)

        # Schedule automatic resume
        if self._resume_task and not self._resume_task.done():
            self._resume_task.cancel()
        self._resume_task = asyncio.create_task(self._auto_resume_when_ready())

    async def _auto_resume_when_ready(self) -> None:
        try:
            while self.globally_paused:
                now = datetime.now(timezone.utc)
                if self.global_pause_until and now >= self.global_pause_until:
                    await self.resume_all()
                    break
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def resume_all(self) -> None:
        """Resume all active agents if they are globally paused."""
        self.globally_paused = False
        self.global_pause_until = None
        self.global_pause_reason = None

        # Clear persisted pause flag
        try:

            async with get_db_transaction() as session:
                repo = SettingsRepository(session)
                await repo.delete_value_without_commit("agent_pause_until")
        except Exception:
            pass

        # Load all agents that are marked active in DB and start them
        active_agents = await get_active_agents_safe()
        for agent in active_agents:
            await self.start_agent(agent)

    async def _check_pause_from_settings(self) -> None:
        """Check persisted pause_until and apply pause/resume/start as needed."""
        try:
            async with async_session() as session:
                settings_repo = SettingsRepository(session)
                pause_until_str = await settings_repo.get_value("agent_pause_until")

            if pause_until_str:
                pause_until_dt = datetime.fromisoformat(pause_until_str)
                if pause_until_dt.tzinfo is None:
                    pause_until_dt = pause_until_dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if now < pause_until_dt:
                    if not self.globally_paused:
                        seconds = max(1, int((pause_until_dt - now).total_seconds()))
                        await self.pause_all_for(seconds, "Rate limited by LLM provider")
                else:
                    if self.globally_paused:
                        await self.resume_all()
                    else:
                        active_agents = await get_active_agents_safe()
                        for agent in active_agents:
                            if agent.agent_id not in self.agents:
                                await self.start_agent(agent)
                    try:
                        async with get_db_transaction() as session:
                            repo = SettingsRepository(session)
                            await repo.delete_value_without_commit("agent_pause_until")
                    except Exception:
                        pass
            else:
                if not self.globally_paused and not self.agents:
                    active_agents = await get_active_agents_safe()
                    for agent in active_agents:
                        await self.start_agent(agent)
        except Exception:
            pass

    async def start_agent(self, agent: Agent) -> None:
        """Start a single agent"""
        if agent.agent_id in self.agents:
            print(f"Agent {agent.name} already running")
            return

        if self.globally_paused:
            # Do not start new agents while paused
            return

        # Create autonomous agent
        autonomous_agent = AutonomousAgent(agent)
        self.agents[agent.agent_id] = autonomous_agent

        # Start the agent's run_forever task
        task = asyncio.create_task(autonomous_agent.run_forever(), name=f"agent_{agent.name}")
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
                # Apply pause/resume/start based on persisted settings
                await self._check_pause_from_settings()

                # Check each running task
                for agent_id, task in list(self.running_tasks.items()):
                    if task.done():
                        # Task finished unexpectedly
                        try:
                            # Get the exception if any
                            task.result()
                        except Exception as e:
                            print(f"Agent {agent_id} crashed: {e}")
                            self._record_agent_error(agent_id, e)

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
                traceback.print_exc()
                self._record_monitor_error(e)
                await asyncio.sleep(10)


# Global agent manager instance
agent_manager = AgentManager()
