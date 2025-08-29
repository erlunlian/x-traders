"""Add COMPACT to agent_thought_type enum

Revision ID: 7e989fe2d6aa
Revises: 56279191c3ac
Create Date: 2025-08-29 04:15:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e989fe2d6aa"
down_revision: Union[str, Sequence[str], None] = "56279191c3ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include COMPACT in agent_thought_type enum."""
    op.execute("ALTER TYPE agent_thought_type ADD VALUE IF NOT EXISTS 'COMPACT'")


def downgrade() -> None:
    """Downgrade is a no-op because removing enum values in Postgres is non-trivial."""
    pass
