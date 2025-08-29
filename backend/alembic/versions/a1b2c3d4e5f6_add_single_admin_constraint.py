"""Add partial unique index to enforce single admin trader

Revision ID: a1b2c3d4e5f6
Revises: fbf1fb97ab3f
Create Date: 2025-08-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "fbf1fb97ab3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure at most one row has is_admin = TRUE using a partial unique index
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_single_admin ON trader_accounts (is_admin) WHERE is_admin IS TRUE"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS uq_single_admin")
