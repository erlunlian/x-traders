"""add social feed tables and extend agent_tool_name enum

Revision ID: 8c0c9b8a2d2d
Revises: f329f379b478
Create Date: 2025-08-29 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c0c9b8a2d2d"
down_revision: Union[str, Sequence[str], None] = "f329f379b478"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add social tables and extend enum."""
    # Create social_posts
    op.create_table(
        "social_posts",
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["ai_agents.agent_id"]),
        sa.PrimaryKeyConstraint("post_id"),
    )
    op.create_index(
        op.f("ix_social_posts_created_at"), "social_posts", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_social_posts_ticker"), "social_posts", ["ticker"], unique=False)

    # Create social_comments
    op.create_table(
        "social_comments",
        sa.Column("comment_id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["post_id"], ["social_posts.post_id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["ai_agents.agent_id"]),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index(
        op.f("ix_social_comments_created_at"), "social_comments", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_social_comments_post_id"), "social_comments", ["post_id"], unique=False
    )

    # Create social_likes
    op.create_table(
        "social_likes",
        sa.Column("like_id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["post_id"], ["social_posts.post_id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["ai_agents.agent_id"]),
        sa.PrimaryKeyConstraint("like_id"),
    )
    op.create_index(
        op.f("ix_social_likes_created_at"), "social_likes", ["created_at"], unique=False
    )
    op.create_unique_constraint(
        "uq_social_likes_post_agent", "social_likes", ["post_id", "agent_id"]
    )

    # Extend agent_tool_name enum with social tools if enum exists
    try:
        op.execute("ALTER TYPE agent_tool_name ADD VALUE IF NOT EXISTS 'CREATE_POST'")
        op.execute("ALTER TYPE agent_tool_name ADD VALUE IF NOT EXISTS 'LIKE_POST'")
        op.execute("ALTER TYPE agent_tool_name ADD VALUE IF NOT EXISTS 'ADD_COMMENT'")
        op.execute("ALTER TYPE agent_tool_name ADD VALUE IF NOT EXISTS 'GET_TICKER_POSTS'")
        op.execute("ALTER TYPE agent_tool_name ADD VALUE IF NOT EXISTS 'GET_POST_COMMENTS'")
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema: drop social tables. Enum values remain (non-trivial to remove)."""
    op.drop_constraint("uq_social_likes_post_agent", "social_likes", type_="unique")
    op.drop_index(op.f("ix_social_likes_created_at"), table_name="social_likes")
    op.drop_table("social_likes")
    op.drop_index(op.f("ix_social_comments_post_id"), table_name="social_comments")
    op.drop_index(op.f("ix_social_comments_created_at"), table_name="social_comments")
    op.drop_table("social_comments")
    op.drop_index(op.f("ix_social_posts_ticker"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_created_at"), table_name="social_posts")
    op.drop_table("social_posts")
