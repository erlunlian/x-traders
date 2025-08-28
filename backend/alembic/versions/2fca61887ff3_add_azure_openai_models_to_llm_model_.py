"""Add Azure OpenAI models to llm_model enum

Revision ID: 2fca61887ff3
Revises: 0ba67b80fce1
Create Date: 2025-08-28 15:54:41.921814

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2fca61887ff3"
down_revision: Union[str, Sequence[str], None] = "0ba67b80fce1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new Azure OpenAI models to the llm_model enum
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4O_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4O_MINI_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_5_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_5_MINI_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_5_NANO_AZURE'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing values from enums
    # So we can't actually downgrade this change
    pass
