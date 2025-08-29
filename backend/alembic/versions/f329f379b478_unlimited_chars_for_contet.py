"""unlimited chars for contet

Revision ID: f329f379b478
Revises: 7e989fe2d6aa
Create Date: 2025-08-29 15:45:24.223589

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f329f379b478"
down_revision: Union[str, Sequence[str], None] = "7e989fe2d6aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change agent_memory.content to unlimited length (TEXT)
    op.alter_column(
        "agent_memory",
        "content",
        existing_type=sa.String(length=10000),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert agent_memory.content back to VARCHAR(10000)
    op.alter_column(
        "agent_memory",
        "content",
        existing_type=sa.Text(),
        type_=sa.String(length=10000),
        existing_nullable=False,
        nullable=False,
        postgresql_using="LEFT(content, 10000)",
    )
