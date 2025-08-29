"""Change tweet_created_at from string to datetime

Revision ID: eca3356c31e2
Revises: 984881f47ffd
Create Date: 2025-08-29 00:40:08.801495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eca3356c31e2'
down_revision: Union[str, Sequence[str], None] = '984881f47ffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a temporary column for the new datetime values
    op.add_column('x_tweets', sa.Column('tweet_created_at_temp', sa.DateTime(timezone=True), nullable=True))
    
    # Convert existing string dates to datetime using PostgreSQL's to_timestamp
    # Twitter format: 'Wed Jun 25 22:21:48 +0000 2025'
    op.execute("""
        UPDATE x_tweets 
        SET tweet_created_at_temp = 
            CASE 
                WHEN tweet_created_at IS NOT NULL AND tweet_created_at != '' THEN
                    to_timestamp(tweet_created_at, 'Dy Mon DD HH24:MI:SS "+0000" YYYY')
                ELSE
                    NOW()
            END
    """)
    
    # Drop the old column
    op.drop_column('x_tweets', 'tweet_created_at')
    
    # Rename the temp column to the original name
    op.alter_column('x_tweets', 'tweet_created_at_temp',
                    new_column_name='tweet_created_at',
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Create a temporary column for the string values
    op.add_column('x_tweets', sa.Column('tweet_created_at_temp', sa.VARCHAR(length=100), nullable=True))
    
    # Convert datetime back to string in Twitter format
    op.execute("""
        UPDATE x_tweets 
        SET tweet_created_at_temp = 
            to_char(tweet_created_at, 'Dy Mon DD HH24:MI:SS "+0000" YYYY')
    """)
    
    # Drop the datetime column
    op.drop_column('x_tweets', 'tweet_created_at')
    
    # Rename the temp column to the original name
    op.alter_column('x_tweets', 'tweet_created_at_temp',
                    new_column_name='tweet_created_at',
                    nullable=False)
