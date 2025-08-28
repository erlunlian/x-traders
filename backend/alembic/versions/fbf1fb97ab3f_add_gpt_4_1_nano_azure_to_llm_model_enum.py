"""Add GPT_4_1_NANO_AZURE to llm_model enum

Revision ID: fbf1fb97ab3f
Revises: d65e5582af3f
Create Date: 2025-08-28 17:47:48.641675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbf1fb97ab3f'
down_revision: Union[str, Sequence[str], None] = 'd65e5582af3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add OpenAI models with underscores (renamed from GPT_4O to GPT_4_O, etc.)
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4_O'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4_O_MINI'")
    
    # Add Azure OpenAI models with underscores
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4_O_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4_O_MINI_AZURE'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'GPT_4_1_NANO_AZURE'")
    
    # Add renamed Claude models (with underscore between 3 and 5)
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'CLAUDE_3_5_SONNET'")
    op.execute("ALTER TYPE llm_model ADD VALUE IF NOT EXISTS 'CLAUDE_3_5_HAIKU'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing values from enums
    # So we can't actually downgrade this change
    pass
