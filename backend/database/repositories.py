import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    DBAgentDecision,
    DBAgentMemory,
    DBAgentThought,
    DBAIAgent,
    DBLedgerEntry,
    DBMarketDataOutbox,
    DBOrder,
    DBPosition,
    DBSequenceCounter,
    DBTrade,
    DBTraderAccount,
    DBXTweet,
    DBXUser,
)
from enums import (
    AgentAction,
    AgentDecisionTrigger,
    AgentMemoryType,
    AgentThoughtType,
    CancelReason,
    LLMModel,
    MarketDataEventType,
    OrderStatus,
)
from models.schemas import BookState, OrderRequest, TradeData
from models.schemas.agents import (
    Agent,
    AgentMemoryState,
    AgentStats,
    DecisionDetail,
    DecisionInfo,
    MemoryInfo,
    ThoughtInfo,
)
from models.schemas.tweet_feed import TweetForAgent
from models.schemas.x_api import Tweet, UserInfo


class XDataRepository:
    """
    Repository for X/Twitter data caching operations.
    Note: Methods with _in_transaction suffix do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _db_tweet_to_tweet_for_agent(self, tweet: DBXTweet) -> TweetForAgent:
        """Convert database tweet model to TweetForAgent schema"""
        return TweetForAgent(
            tweet_id=str(tweet.tweet_id),
            author_username=str(tweet.author_username),
            author_name=str(tweet.author.name) if tweet.author else None,
            author_followers=int(tweet.author.num_followers) if tweet.author else 0,
            author_following=int(tweet.author.num_following) if tweet.author else 0,
            text=str(tweet.text),
            like_count=int(tweet.like_count),
            retweet_count=int(tweet.retweet_count),
            reply_count=int(tweet.reply_count),
            quote_count=int(tweet.quote_count),
            view_count=int(tweet.view_count),
            fetched_at=datetime.fromisoformat(tweet.fetched_at.isoformat()),
        )

    def _db_user_to_user_info(self, user: DBXUser) -> UserInfo:
        """Convert database user model to UserInfo schema"""
        return UserInfo(
            username=user.username,
            name=user.name,
            description=user.description,
            location=user.location,
            num_followers=user.num_followers,
            num_following=user.num_following,
        )

    async def upsert_user_without_commit(self, user_info: UserInfo) -> UserInfo:
        """
        Insert or update user information in cache.
        Must be called within a transaction context - does NOT commit.
        """
        stmt = (
            insert(DBXUser)
            .values(
                username=user_info.username,
                name=user_info.name,
                description=user_info.description,
                location=user_info.location,
                num_followers=user_info.num_followers,
                num_following=user_info.num_following,
                fetched_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["username"],
                set_={
                    "name": user_info.name,
                    "description": user_info.description,
                    "location": user_info.location,
                    "num_followers": user_info.num_followers,
                    "num_following": user_info.num_following,
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXUser)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        user = result.scalar_one()
        return self._db_user_to_user_info(user)

    async def upsert_tweet_without_commit(
        self, tweet: Tweet, author_username: str
    ) -> DBXTweet:
        """
        Insert or update tweet in cache.
        Must be called within a transaction context - does NOT commit.

        Args:
            tweet: Tweet model from API
            author_username: Username of tweet author (must exist in x_users table)
        """
        # Convert entities to dict if present
        entities_dict = None
        if tweet.entities:
            entities_dict = tweet.entities.model_dump()

        stmt = (
            insert(DBXTweet)
            .values(
                tweet_id=tweet.tweet_id,
                author_username=author_username,
                text=tweet.text,
                retweet_count=tweet.retweet_count,
                reply_count=tweet.reply_count,
                like_count=tweet.like_count,
                quote_count=tweet.quote_count,
                view_count=tweet.view_count,
                bookmark_count=tweet.bookmark_count,
                is_reply=tweet.is_reply,
                reply_to_tweet_id=tweet.reply_to_tweet_id,
                conversation_id=tweet.conversation_id,
                in_reply_to_username=tweet.in_reply_to_username,
                quoted_tweet_id=tweet.quoted_tweet_id,
                retweeted_tweet_id=tweet.retweeted_tweet_id,
                entities=entities_dict,
                tweet_created_at=tweet.created_at,
                fetched_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["tweet_id"],
                set_={
                    "text": tweet.text,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "like_count": tweet.like_count,
                    "quote_count": tweet.quote_count,
                    "view_count": tweet.view_count,
                    "bookmark_count": tweet.bookmark_count,
                    "is_reply": tweet.is_reply,
                    "reply_to_tweet_id": tweet.reply_to_tweet_id,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_username": tweet.in_reply_to_username,
                    "quoted_tweet_id": tweet.quoted_tweet_id,
                    "retweeted_tweet_id": tweet.retweeted_tweet_id,
                    "entities": entities_dict,
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def get_user_or_none(self, username: str) -> Optional[UserInfo]:
        """Get cached user by username - returns None if not found"""
        result = await self.session.execute(
            select(DBXUser).where(DBXUser.username == username)
        )
        user = result.scalar_one_or_none()
        return self._db_user_to_user_info(user) if user else None

    async def get_tweet_or_none(self, tweet_id: str) -> Optional[DBXTweet]:
        """Get cached tweet by ID - returns None if not found"""
        result = await self.session.execute(
            select(DBXTweet).where(DBXTweet.tweet_id == tweet_id)
        )
        return result.scalar_one_or_none()

    async def get_tweets_by_username(
        self, username: str, limit: int = 20
    ) -> List[DBXTweet]:
        """
        Get cached tweets for a user, ordered by tweet creation time (newest first).

        Args:
            username: Twitter username
            limit: Maximum number of tweets to return
        """
        result = await self.session.execute(
            select(DBXTweet)
            .where(DBXTweet.author_username == username)
            .order_by(DBXTweet.tweet_created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_tweets_by_ids(self, tweet_ids: List[str]) -> List[DBXTweet]:
        """
        Get multiple cached tweets by their IDs.

        Args:
            tweet_ids: List of tweet IDs to fetch

        Returns:
            List of cached tweets (may be fewer than requested if some aren't cached)
        """
        if not tweet_ids:
            return []

        result = await self.session.execute(
            select(DBXTweet).where(DBXTweet.tweet_id.in_(tweet_ids))
        )
        return list(result.scalars().all())

    async def bulk_upsert_tweets_in_without_commit(
        self, tweets: List[Tweet], author_username: str
    ) -> List[DBXTweet]:
        """
        Bulk insert or update multiple tweets.
        More efficient than individual upserts for multiple tweets.
        Must be called within a transaction context - does NOT commit.

        Args:
            tweets: List of Tweet models from API
            author_username: Username of tweet author (must exist in x_users table)
        """
        if not tweets:
            return []

        # Prepare values for bulk insert
        values = []
        for tweet in tweets:
            entities_dict = None
            if tweet.entities:
                entities_dict = tweet.entities.model_dump()

            values.append(
                {
                    "tweet_id": tweet.tweet_id,
                    "author_username": author_username,
                    "text": tweet.text,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "like_count": tweet.like_count,
                    "quote_count": tweet.quote_count,
                    "view_count": tweet.view_count,
                    "bookmark_count": tweet.bookmark_count,
                    "is_reply": tweet.is_reply,
                    "reply_to_tweet_id": tweet.reply_to_tweet_id,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_username": tweet.in_reply_to_username,
                    "quoted_tweet_id": tweet.quoted_tweet_id,
                    "retweeted_tweet_id": tweet.retweeted_tweet_id,
                    "entities": entities_dict,
                    "tweet_created_at": tweet.created_at,
                    "fetched_at": datetime.utcnow(),
                }
            )

        stmt = (
            insert(DBXTweet)
            .values(values)
            .on_conflict_do_update(
                index_elements=["tweet_id"],
                set_={
                    "text": insert(DBXTweet).excluded.text,
                    "retweet_count": insert(DBXTweet).excluded.retweet_count,
                    "reply_count": insert(DBXTweet).excluded.reply_count,
                    "like_count": insert(DBXTweet).excluded.like_count,
                    "quote_count": insert(DBXTweet).excluded.quote_count,
                    "view_count": insert(DBXTweet).excluded.view_count,
                    "bookmark_count": insert(DBXTweet).excluded.bookmark_count,
                    "is_reply": insert(DBXTweet).excluded.is_reply,
                    "reply_to_tweet_id": insert(DBXTweet).excluded.reply_to_tweet_id,
                    "conversation_id": insert(DBXTweet).excluded.conversation_id,
                    "in_reply_to_username": insert(
                        DBXTweet
                    ).excluded.in_reply_to_username,
                    "quoted_tweet_id": insert(DBXTweet).excluded.quoted_tweet_id,
                    "retweeted_tweet_id": insert(DBXTweet).excluded.retweeted_tweet_id,
                    "entities": insert(DBXTweet).excluded.entities,
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())

    async def get_all_users(self) -> List[UserInfo]:
        """
        Get all users from the database.

        Returns:
            List of all cached users
        """
        result = await self.session.execute(select(DBXUser))
        users = list(result.scalars().all())
        return [self._db_user_to_user_info(user) for user in users]

    async def get_all_tweets(self) -> List[DBXTweet]:
        """
        Get all tweets from the database.

        Returns:
            List of all cached tweets
        """
        result = await self.session.execute(
            select(DBXTweet).order_by(DBXTweet.tweet_created_at.desc())
        )
        return list(result.scalars().all())

    async def get_tweets_after_timestamp(
        self, after_timestamp: Optional[datetime], limit: int = 100
    ) -> List[DBXTweet]:
        """
        Get tweets newer than a given timestamp, with user data.

        Args:
            after_timestamp: Get tweets fetched after this time. If None, gets latest tweets.
            limit: Maximum number of tweets to return

        Returns:
            List of tweets with author data loaded
        """
        from sqlalchemy.orm import selectinload

        query = select(DBXTweet).options(selectinload(DBXTweet.author))

        if after_timestamp:
            query = query.where(DBXTweet.fetched_at > after_timestamp)

        # Order by fetched_at to process in chronological order
        query = query.order_by(DBXTweet.fetched_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tweets_for_agent(
        self, after_timestamp: Optional[datetime], limit: int = 100
    ) -> List[TweetForAgent]:
        """
        Get tweets as TweetForAgent models for agent processing.
        Uses mapper to convert SQLAlchemy models to Pydantic models.
        """
        tweets = await self.get_tweets_after_timestamp(after_timestamp, limit)
        return [self._db_tweet_to_tweet_for_agent(tweet) for tweet in tweets]


class AgentRepository:
    """Repository for AI agent operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_db_agent(self, agent_id: UUID) -> DBAIAgent:
        """Get agent database model - internal use only"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.agent_id == agent_id)
        )
        return result.scalar_one()

    async def _get_db_agent_or_none(self, agent_id: UUID) -> Optional[DBAIAgent]:
        """Get agent database model or None - internal use only"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agent(self, agent_id: UUID) -> Agent:
        """Get agent"""
        agent = await self._get_db_agent(agent_id)
        return self._db_to_agent(agent)

    async def get_agent_by_name(self, name: str) -> Agent:
        """Get agent by name"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.name == name)
        )
        agent = result.scalar_one()
        return self._db_to_agent(agent)

    async def get_agent_or_none(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent database record or None if not found"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()
        return self._db_to_agent(agent) if agent else None

    async def get_agent_by_name_or_none(self, name: str) -> Optional[Agent]:
        """Get agent database record by name or None if not found"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.name == name)
        )
        agent = result.scalar_one_or_none()
        return self._db_to_agent(agent) if agent else None

    def _db_to_agent(self, agent: DBAIAgent) -> Agent:
        """Convert DB model to Pydantic model"""
        return Agent(
            agent_id=agent.agent_id,
            name=agent.name,
            trader_id=agent.trader_id,
            llm_model=agent.llm_model,
            temperature=agent.temperature,
            system_prompt=agent.system_prompt,
            is_active=agent.is_active,
            total_decisions=agent.total_decisions,
            last_decision_at=agent.last_decision_at,
            created_at=agent.created_at,
            last_processed_tweet_at=agent.last_processed_tweet_at,
        )

    async def create_agent_without_commit(
        self,
        name: str,
        trader_id: UUID,
        llm_model: LLMModel,
        system_prompt: str,
        temperature: float = 0.7,
        is_active: bool = True,
    ) -> Agent:
        """Create a new AI agent"""
        agent = DBAIAgent(
            name=name,
            trader_id=trader_id,
            llm_model=llm_model,
            system_prompt=system_prompt,
            temperature=temperature,
            is_active=is_active,
        )
        self.session.add(agent)
        await self.session.flush()

        return self._db_to_agent(agent)

    async def list_agents(
        self,
        trader_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Agent]:
        """List agents with optional filters"""
        query = select(DBAIAgent)

        if trader_id:
            query = query.where(DBAIAgent.trader_id == trader_id)
        if is_active is not None:
            query = query.where(DBAIAgent.is_active == is_active)

        query = query.order_by(desc(DBAIAgent.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        agents = result.scalars().all()

        return [self._db_to_agent(agent) for agent in agents]

    async def update_agent_without_commit(
        self,
        agent_id: UUID,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Agent]:
        """Update agent configuration"""
        agent_db = await self._get_db_agent_or_none(agent_id)

        if not agent_db:
            return None

        if temperature is not None:
            agent_db.temperature = temperature
        if system_prompt is not None:
            agent_db.system_prompt = system_prompt
        if is_active is not None:
            agent_db.is_active = is_active

        await self.session.flush()

        return self._db_to_agent(agent_db)

    async def record_decision_without_commit(
        self,
        agent_id: UUID,
        trigger_type: AgentDecisionTrigger,
        action: AgentAction,
        thoughts: List[tuple[AgentThoughtType, str]],  # (type, content) pairs
        ticker: Optional[str] = None,
        quantity: Optional[int] = None,
        reasoning: Optional[str] = None,
        trigger_tweet_id: Optional[str] = None,
        order_id: Optional[UUID] = None,
        executed: bool = False,
    ) -> DecisionDetail:
        """Record an agent decision with thought trail"""
        # Get agent for name
        agent_db = await self._get_db_agent_or_none(agent_id)
        if not agent_db:
            raise ValueError(f"Agent {agent_id} not found")

        # Create decision record
        decision = DBAgentDecision(
            agent_id=agent_id,
            trigger_type=trigger_type,
            trigger_tweet_id=trigger_tweet_id,
            action=action,
            ticker=ticker,
            quantity=quantity,
            reasoning=reasoning,
            order_id=order_id,
            executed=executed,
        )
        self.session.add(decision)
        await self.session.flush()

        # Create thought records
        thought_records = []
        for i, (thought_type, content) in enumerate(thoughts):
            thought = DBAgentThought(
                decision_id=decision.decision_id,
                agent_id=agent_id,
                step_number=i + 1,
                thought_type=thought_type,
                content=content,
            )
            self.session.add(thought)
            thought_records.append(thought)

        await self.session.flush()

        # Update agent stats
        agent_db.total_decisions += 1
        agent_db.last_decision_at = decision.created_at
        await self.session.flush()

        return DecisionDetail(
            decision_id=decision.decision_id,
            agent_id=decision.agent_id,
            agent_name=agent_db.name,
            trigger_type=decision.trigger_type,
            trigger_tweet_id=decision.trigger_tweet_id,
            action=decision.action,
            ticker=decision.ticker,
            quantity=decision.quantity,
            reasoning=decision.reasoning,
            order_id=decision.order_id,
            executed=decision.executed,
            created_at=decision.created_at,
            thoughts=[
                ThoughtInfo(
                    thought_id=t.thought_id,
                    step_number=t.step_number,
                    thought_type=t.thought_type,
                    content=t.content,
                    created_at=t.created_at,
                )
                for t in thought_records
            ],
        )

    async def get_decision(self, decision_id: UUID) -> Optional[DecisionDetail]:
        """Get decision with full thought trail"""
        result = await self.session.execute(
            select(DBAgentDecision)
            .options(selectinload(DBAgentDecision.thoughts))
            .options(selectinload(DBAgentDecision.agent))
            .where(DBAgentDecision.decision_id == decision_id)
        )
        decision = result.scalar_one_or_none()

        if not decision:
            return None

        return DecisionDetail(
            decision_id=decision.decision_id,
            agent_id=decision.agent_id,
            agent_name=decision.agent.name if decision.agent else "Unknown",
            trigger_type=decision.trigger_type,
            trigger_tweet_id=decision.trigger_tweet_id,
            action=decision.action,
            ticker=decision.ticker,
            quantity=decision.quantity,
            reasoning=decision.reasoning,
            order_id=decision.order_id,
            executed=decision.executed,
            created_at=decision.created_at,
            thoughts=[
                ThoughtInfo(
                    thought_id=t.thought_id,
                    step_number=t.step_number,
                    thought_type=t.thought_type,
                    content=t.content,
                    created_at=t.created_at,
                )
                for t in sorted(decision.thoughts, key=lambda x: x.step_number)
            ],
        )

    async def list_agent_decisions(
        self,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_thoughts: bool = False,
    ) -> List[DecisionInfo]:
        """List decisions for an agent"""
        query = select(DBAgentDecision).where(DBAgentDecision.agent_id == agent_id)

        if include_thoughts:
            query = query.options(selectinload(DBAgentDecision.thoughts))

        query = (
            query.order_by(desc(DBAgentDecision.created_at)).limit(limit).offset(offset)
        )

        result = await self.session.execute(query)
        decisions = result.scalars().all()

        return [
            DecisionInfo(
                decision_id=d.decision_id,
                agent_id=d.agent_id,
                trigger_type=d.trigger_type,
                trigger_tweet_id=d.trigger_tweet_id,
                action=d.action,
                ticker=d.ticker,
                quantity=d.quantity,
                reasoning=d.reasoning,
                order_id=d.order_id,
                executed=d.executed,
                created_at=d.created_at,
            )
            for d in decisions
        ]

    async def save_memory_without_commit(
        self,
        agent_id: UUID,
        memory_type: AgentMemoryType,
        content: str,
        token_count: int,
    ) -> MemoryInfo:
        """Save agent memory snapshot"""
        # If saving working memory, delete old working memory
        if memory_type == AgentMemoryType.WORKING:
            result = await self.session.execute(
                select(DBAgentMemory).where(
                    and_(
                        DBAgentMemory.agent_id == agent_id,
                        DBAgentMemory.memory_type == AgentMemoryType.WORKING,
                    )
                )
            )
            old_working = result.scalar_one_or_none()

            if old_working:
                await self.session.delete(old_working)

        memory = DBAgentMemory(
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            token_count=token_count,
        )
        self.session.add(memory)
        await self.session.flush()

        return MemoryInfo(
            memory_id=memory.memory_id,
            memory_type=memory.memory_type,
            content=memory.content,
            token_count=memory.token_count,
            created_at=memory.created_at,
        )

    async def get_agent_memory(self, agent_id: UUID) -> AgentMemoryState:
        """Get current memory state for an agent"""
        result = await self.session.execute(
            select(DBAgentMemory)
            .where(DBAgentMemory.agent_id == agent_id)
            .order_by(desc(DBAgentMemory.created_at))
        )
        memories = result.scalars().all()

        working_memory = None
        compressed_memories = []
        total_tokens = 0

        for memory in memories:
            memory_info = MemoryInfo(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                content=memory.content,
                token_count=memory.token_count,
                created_at=memory.created_at,
            )

            if memory.memory_type == AgentMemoryType.WORKING:
                working_memory = memory_info
            else:
                compressed_memories.append(memory_info)

            total_tokens += memory.token_count

        return AgentMemoryState(
            agent_id=agent_id,
            working_memory=working_memory,
            compressed_memories=compressed_memories,
            total_tokens=total_tokens,
        )

    async def get_agent_stats(self, agent_id: UUID) -> Optional[AgentStats]:
        """Get comprehensive agent statistics"""
        # Get agent
        agent = await self.get_agent_or_none(agent_id)

        if not agent:
            return None

        # Get action breakdown
        action_counts = await self.session.execute(
            select(
                DBAgentDecision.action,
                func.count(DBAgentDecision.decision_id).label("count"),
            )
            .where(DBAgentDecision.agent_id == agent_id)
            .group_by(DBAgentDecision.action)
        )

        action_breakdown = {row.action.value: row.count for row in action_counts}

        # Count trade decisions and executed trades
        trade_decisions = await self.session.execute(
            select(func.count(DBAgentDecision.decision_id)).where(
                and_(
                    DBAgentDecision.agent_id == agent_id,
                    DBAgentDecision.action.in_([AgentAction.BUY, AgentAction.SELL]),
                )
            )
        )
        trade_count = trade_decisions.scalar() or 0

        executed_trades = await self.session.execute(
            select(func.count(DBAgentDecision.decision_id)).where(
                and_(
                    DBAgentDecision.agent_id == agent_id,
                    DBAgentDecision.action.in_([AgentAction.BUY, AgentAction.SELL]),
                    DBAgentDecision.executed,
                )
            )
        )
        executed_count = executed_trades.scalar() or 0

        execution_rate = (
            (executed_count / trade_count * 100) if trade_count > 0 else 0.0
        )

        return AgentStats(
            agent_id=agent.agent_id,
            name=agent.name,
            llm_model=agent.llm_model,
            is_active=agent.is_active,
            total_decisions=agent.total_decisions,
            last_decision_at=agent.last_decision_at,
            action_breakdown=action_breakdown,
            trade_decisions=trade_count,
            executed_trades=executed_count,
            execution_rate=execution_rate,
        )

    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents"""
        result = await self.session.execute(
            select(DBAIAgent).where(DBAIAgent.is_active).order_by(DBAIAgent.name)
        )
        agents = result.scalars().all()

        return [self._db_to_agent(agent) for agent in agents]

    async def update_last_processed_tweet_without_commit(
        self, agent_id: UUID, timestamp: datetime
    ):
        """Update the last processed tweet timestamp for an agent"""
        agent_db = await self._get_db_agent_or_none(agent_id)
        if agent_db:
            agent_db.last_processed_tweet_at = timestamp
            await self.session.flush()

    async def save_orphan_thought_without_commit(
        self,
        agent_id: UUID,
        thought_type: AgentThoughtType,
        content: str,
        step_number: int = 0,
    ):
        """Save a thought that's not associated with a specific decision"""
        thought = DBAgentThought(
            agent_id=agent_id,
            decision_id=None,  # Orphan thought, not tied to a decision
            step_number=step_number,
            thought_type=thought_type,
            content=content[:2000],  # Truncate to field limit
        )
        self.session.add(thought)
        await self.session.flush()

    async def cleanup_old_memories_without_commit(
        self,
        agent_id: UUID,
        keep_last_n: int = 10,
    ) -> int:
        """Clean up old compressed memories, keeping the most recent N"""
        # Get compressed memories ordered by creation time
        result = await self.session.execute(
            select(DBAgentMemory)
            .where(
                and_(
                    DBAgentMemory.agent_id == agent_id,
                    DBAgentMemory.memory_type == AgentMemoryType.COMPRESSED,
                )
            )
            .order_by(desc(DBAgentMemory.created_at))
        )
        memories = result.scalars().all()

        # Delete all but the most recent N
        deleted_count = 0
        for memory in memories[keep_last_n:]:
            await self.session.delete(memory)
            deleted_count += 1

        return deleted_count


class OrderRepository:
    """
    Repository for order operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_sequence(self, ticker: str) -> int:
        """Atomic UPSERT for sequence - handles race on first insert"""
        stmt = (
            insert(DBSequenceCounter)
            .values(ticker=ticker, last_sequence=1)
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={"last_sequence": DBSequenceCounter.last_sequence + 1},
            )
            .returning(DBSequenceCounter.last_sequence)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create_order_without_commit(
        self, order_request: OrderRequest, expires_at: datetime
    ) -> DBOrder:
        """
        Create order with sequence number.
        Must be called within a transaction context - does NOT commit.
        """
        sequence = await self.get_next_sequence(order_request.ticker)

        order = DBOrder(
            trader_id=order_request.trader_id,
            ticker=order_request.ticker,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            limit_price=order_request.limit_price_in_cents,
            filled_quantity=0,
            status=OrderStatus.PENDING,
            sequence=sequence,
            tif_seconds=order_request.tif_seconds,
            expires_at=expires_at,
        )
        self.session.add(order)
        await self.session.flush()  # Get ID but stay in transaction
        return order

    async def get_order(self, order_id: uuid.UUID) -> DBOrder:
        """Get order by ID - raises if not found"""
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id)
        )
        return result.scalar_one()

    async def get_order_or_none(self, order_id: uuid.UUID) -> Optional[DBOrder]:
        """Get order by ID - returns None if not found"""
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_filled_without_commit(
        self, order_id: uuid.UUID, fill_quantity: int
    ):
        """
        Update order filled quantity and status.
        Validates that filled quantity doesn't exceed order quantity.
        """
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id).with_for_update()
        )
        order = result.scalar_one()

        new_filled = order.filled_quantity + fill_quantity
        if new_filled > order.quantity:
            raise ValueError(
                f"Fill quantity {new_filled} exceeds order quantity {order.quantity}"
            )

        order.filled_quantity = new_filled

        # Update status based on fill
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL
        # else stays PENDING

    async def get_unfilled_orders(self, ticker: str) -> List[DBOrder]:
        """Get all unfilled orders for building order book"""
        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.ticker == ticker)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(DBOrder.sequence)
        )
        return result.scalars().all()

    async def get_trader_unfilled_orders(self, trader_id: uuid.UUID) -> List[DBOrder]:
        """Get all unfilled orders for a specific trader"""
        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.trader_id == trader_id)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(DBOrder.created_at.desc())
        )
        return result.scalars().all()

    async def get_expired_orders(self, limit: int = 100) -> List[DBOrder]:
        """Get orders that have exceeded their TIF"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.expires_at <= now)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .limit(limit)
        )
        return result.scalars().all()

    async def cancel_order_without_commit(
        self, order_id: uuid.UUID, cancel_reason: CancelReason
    ) -> DBOrder:
        """
        Cancel an order with the specified reason.
        Must be called within a transaction context - does NOT commit.
        Raises if order not found.
        """

        order = await self.get_order(order_id)  # Will raise if not found

        # Only cancel if order is still active
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            raise ValueError(
                f"Cannot cancel order {order_id} with status {order.status}"
            )

        # Update status based on reason
        if cancel_reason == CancelReason.USER:
            order.status = OrderStatus.CANCELLED
        else:
            order.status = OrderStatus.EXPIRED

        order.cancel_reason = cancel_reason
        return order


class TradeRepository:
    """
    Repository for trade operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_trade_without_commit(self, trade_data: TradeData) -> DBTrade:
        """
        Record trade execution.
        Must be called within a transaction context - does NOT commit.
        """
        trade = DBTrade(
            buy_order_id=trade_data.buy_order_id,
            sell_order_id=trade_data.sell_order_id,
            ticker=trade_data.ticker,
            price=trade_data.price_in_cents,
            quantity=trade_data.quantity,
            buyer_id=trade_data.buyer_id,
            seller_id=trade_data.seller_id,
            taker_order_id=trade_data.taker_order_id,
            maker_order_id=trade_data.maker_order_id,
            executed_at=trade_data.executed_at or datetime.now(timezone.utc),
        )
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def get_recent_trades(self, ticker: str, limit: int = 50) -> List[DBTrade]:
        result = await self.session.execute(
            select(DBTrade)
            .where(DBTrade.ticker == ticker)
            .order_by(DBTrade.executed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_trader_trades(
        self, trader_id: uuid.UUID, limit: int = 50
    ) -> List[DBTrade]:
        """Get recent trades for a specific trader (as buyer or seller)"""
        from sqlalchemy import or_

        result = await self.session.execute(
            select(DBTrade)
            .where(or_(DBTrade.buyer_id == trader_id, DBTrade.seller_id == trader_id))
            .order_by(DBTrade.executed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_ohlc_history(
        self, ticker: str, interval: str, periods: int
    ) -> List[Dict]:
        """
        Get OHLC (Open, High, Low, Close) data for a ticker.

        Args:
            ticker: The ticker symbol
            interval: PostgreSQL interval string (e.g., '1 hour', '1 day', '1 week')
            periods: Number of periods to return

        Returns:
            List of dicts with timestamp, open, high, low, close, volume
        """
        from datetime import datetime, timedelta, timezone

        # Determine time window and truncation
        now = datetime.now(timezone.utc)
        if interval == "1 hour":
            start_time = now - timedelta(hours=periods)
            trunc = "hour"
        elif interval == "6 hours":
            start_time = now - timedelta(hours=periods * 6)
            trunc = "hour"  # Still truncate by hour, but we'll group by 6-hour periods
        elif interval == "1 day":
            start_time = now - timedelta(days=periods)
            trunc = "day"
        elif interval == "1 week":
            start_time = now - timedelta(weeks=periods)
            trunc = "week"
        else:
            # Default fallback
            start_time = now - timedelta(days=30)
            trunc = "day"

        # Simpler query using GROUP BY instead of window functions for the main aggregation
        from sqlalchemy import text

        query = text(
            """
            WITH time_periods AS (
                SELECT 
                    date_trunc(:trunc, executed_at) AS period,
                    MIN(executed_at) AS first_trade_time,
                    MAX(executed_at) AS last_trade_time
                FROM trades
                WHERE ticker = :ticker
                    AND executed_at >= :start_time
                GROUP BY date_trunc(:trunc, executed_at)
            ),
            period_ohlc AS (
                SELECT 
                    tp.period,
                    -- Get first trade price (open)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.first_trade_time 
                     LIMIT 1) AS open,
                    -- Get last trade price (close)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.last_trade_time 
                     LIMIT 1) AS close,
                    -- Get high/low/volume for the period
                    MAX(t.price) AS high,
                    MIN(t.price) AS low,
                    SUM(t.quantity) AS volume
                FROM time_periods tp
                JOIN trades t ON t.ticker = :ticker 
                    AND date_trunc(:trunc, t.executed_at) = tp.period
                GROUP BY tp.period, tp.first_trade_time, tp.last_trade_time
            )
            SELECT 
                period AS timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM period_ohlc
            ORDER BY period ASC
        """
        )

        result = await self.session.execute(
            query,
            {
                "ticker": ticker,
                "trunc": trunc,
                "start_time": start_time,
            },
        )

        rows = result.fetchall()

        # Convert to list of dicts
        ohlc_data = []
        for row in rows:
            ohlc_data.append(
                {
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": int(row.volume) if row.volume else 0,
                }
            )

        # If we need to group 6-hour periods, do it in Python
        if interval == "6 hours":
            grouped_data = []
            i = 0
            while i < len(ohlc_data):
                # Take up to 6 hourly candles and combine them
                group = ohlc_data[i : min(i + 6, len(ohlc_data))]
                if group:
                    grouped_data.append(
                        {
                            "timestamp": group[0]["timestamp"],
                            "open": group[0]["open"],
                            "high": max(g["high"] for g in group),
                            "low": min(g["low"] for g in group),
                            "close": group[-1]["close"],
                            "volume": sum(g["volume"] for g in group),
                        }
                    )
                i += 6
            ohlc_data = grouped_data

        return ohlc_data


class PositionRepository:
    """
    Repository for position tracking.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_for_buy_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int, price_in_cents: int
    ):
        """Update position and avg_cost for buy"""
        # Get current position with lock
        result = await self.session.execute(
            select(DBPosition)
            .where(and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if position:
            # Update avg_cost: (old_qty * old_avg + new_qty * price) / total_qty
            new_qty = position.quantity + quantity
            new_avg = (
                ((position.quantity * position.avg_cost) + (quantity * price_in_cents))
                // new_qty
                if new_qty > 0
                else 0
            )

            position.quantity = new_qty
            position.avg_cost = new_avg
        else:
            # Create new position
            position = DBPosition(
                trader_id=trader_id,
                ticker=ticker,
                quantity=quantity,
                avg_cost=price_in_cents,
            )
            self.session.add(position)

    async def update_for_sell_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int
    ):
        """Update position for sell - avg_cost remains unchanged"""
        result = await self.session.execute(
            select(DBPosition)
            .where(and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if not position or position.quantity < quantity:
            raise ValueError(
                f"Insufficient shares: trying to sell {quantity}, have {position.quantity if position else 0}"
            )

        position.quantity -= quantity

    async def get_position(self, trader_id: uuid.UUID, ticker: str) -> DBPosition:
        """Get position - raises if not found"""
        result = await self.session.execute(
            select(DBPosition).where(
                and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker)
            )
        )
        return result.scalar_one()

    async def get_position_or_none(
        self, trader_id: uuid.UUID, ticker: str
    ) -> Optional[DBPosition]:
        """Get position - returns None if not found"""
        result = await self.session.execute(
            select(DBPosition).where(
                and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker)
            )
        )
        return result.scalar_one_or_none()

    async def get_all_positions(self, trader_id: uuid.UUID) -> List[DBPosition]:
        """Get all positions for a trader"""
        result = await self.session.execute(
            select(DBPosition)
            .where(DBPosition.trader_id == trader_id)
            .where(DBPosition.quantity > 0)
        )
        return result.scalars().all()


class LedgerRepository:
    """
    Repository for double-entry bookkeeping.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def post_trade_entries_without_commit(self, trade: DBTrade):
        """Post double-entry for trade execution"""
        # Cash entries
        cash_entries = [
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account="CASH",
                debit_in_cents=trade.price * trade.quantity,
                credit_in_cents=0,
                description=f"Buy {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account="CASH",
                debit_in_cents=0,
                credit_in_cents=trade.price * trade.quantity,
                description=f"Sell {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
        ]

        # Share entries (stored as quantity, not cents)
        share_entries = [
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=trade.quantity,  # Using cents field for quantity
                credit_in_cents=0,
                description=f"Receive {trade.quantity} shares",
            ),
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=0,
                credit_in_cents=trade.quantity,  # Using cents field for quantity
                description=f"Deliver {trade.quantity} shares",
            ),
        ]

        for entry in cash_entries + share_entries:
            self.session.add(entry)

    async def get_cash_balance_in_cents(self, trader_id: uuid.UUID) -> int:
        """Get current cash balance in cents"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(DBLedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(DBLedgerEntry.credit_in_cents), 0)
            )
            .where(DBLedgerEntry.trader_id == trader_id)
            .where(DBLedgerEntry.account == "CASH")
        )
        return result.scalar() or 0

    async def get_share_balance(self, trader_id: uuid.UUID, ticker: str) -> int:
        """Get share balance (quantity, not cents)"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(DBLedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(DBLedgerEntry.credit_in_cents), 0)
            )
            .where(DBLedgerEntry.trader_id == trader_id)
            .where(DBLedgerEntry.account == f"SHARES:{ticker}")
        )
        return result.scalar() or 0

    async def initialize_trader_cash_without_commit(
        self, trader_id: uuid.UUID, initial_cash_in_cents: int
    ):
        """
        Give trader starting cash.
        Must be called within a transaction context - does NOT commit.
        """
        entry = DBLedgerEntry(
            trader_id=trader_id,
            account="CASH",
            debit_in_cents=initial_cash_in_cents,
            credit_in_cents=0,
            description=f"Initial deposit: ${initial_cash_in_cents/100:.2f}",
        )
        self.session.add(entry)


class OutboxRepository:
    """
    Repository for market data outbox pattern.
    Note: Methods do NOT commit except publish_batch which is autonomous.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def queue_trade_event_without_commit(
        self, trade_data: TradeData, book_state: BookState
    ):
        """
        Queue trade event with book state.
        Does NOT commit - must be called within trade transaction.
        """
        event = DBMarketDataOutbox(
            event_type=MarketDataEventType.TRADE,
            ticker=trade_data.ticker,
            payload={
                "trade": {
                    "price_in_cents": trade_data.price_in_cents,
                    "quantity": trade_data.quantity,
                    "timestamp": (
                        trade_data.executed_at or datetime.now(timezone.utc)
                    ).isoformat(),
                },
                "book": {
                    "best_bid_in_cents": book_state.best_bid_in_cents,
                    "best_ask_in_cents": book_state.best_ask_in_cents,
                    "bid_size": book_state.bid_size,
                    "ask_size": book_state.ask_size,
                },
            },
        )
        self.session.add(event)

    async def publish_batch_with_commit(
        self, redis_client=None, limit: int = 100
    ) -> int:
        """
        Atomically claim and publish outbox events.
        This DOES commit as it's a separate autonomous transaction.
        Uses skip_locked to allow multiple workers without contention.
        """
        # Use FOR UPDATE SKIP LOCKED to avoid contention between workers
        result = await self.session.execute(
            select(DBMarketDataOutbox)
            .where(~DBMarketDataOutbox.published)
            .order_by(DBMarketDataOutbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)  # Skip rows locked by other workers
        )
        events = result.scalars().all()

        if events and redis_client:
            # Publish to Redis/WebSocket
            for event in events:
                channel = f"{event.event_type.value.lower()}.{event.ticker}"
                await redis_client.publish(channel, event.payload)

            # Mark as published
            event_ids = [e.event_id for e in events]
            await self.session.execute(
                update(DBMarketDataOutbox)
                .where(DBMarketDataOutbox.event_id.in_(event_ids))
                .values(published=True)
            )
            await self.session.commit()  # Autonomous commit for outbox

        return len(events)


class TraderRepository:
    """
    Repository for trader accounts.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trader_in_transaction_without_commit(
        self,
        trader_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> DBTraderAccount:
        """
        Create a new trader account.
        Must be called within a transaction context - does NOT commit.
        """
        trader = DBTraderAccount(
            trader_id=trader_id or uuid.uuid4(),
            is_active=True,
            is_admin=is_admin,
        )
        self.session.add(trader)
        await self.session.flush()
        return trader

    async def get_trader(self, trader_id: uuid.UUID) -> DBTraderAccount:
        """Get trader - raises if not found"""
        result = await self.session.execute(
            select(DBTraderAccount).where(DBTraderAccount.trader_id == trader_id)
        )
        return result.scalar_one()

    async def get_trader_or_none(
        self, trader_id: uuid.UUID
    ) -> Optional[DBTraderAccount]:
        """Get trader - returns None if not found"""
        result = await self.session.execute(
            select(DBTraderAccount).where(DBTraderAccount.trader_id == trader_id)
        )
        return result.scalar_one_or_none()

    async def get_all_traders(self) -> List[DBTraderAccount]:
        """Get all traders"""
        result = await self.session.execute(
            select(DBTraderAccount)
            .where(DBTraderAccount.is_active)
            .order_by(DBTraderAccount.created_at.desc())
        )
        return result.scalars().all()
