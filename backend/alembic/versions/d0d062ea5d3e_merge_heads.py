"""merge heads

Revision ID: d0d062ea5d3e
Revises: a1b2c3d4e5f6, eca3356c31e2
Create Date: 2025-08-29 03:11:28.339771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0d062ea5d3e'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'eca3356c31e2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
