"""Fix sessions table primary key autoincrement

Revision ID: 281cb7424067
Revises: 57ac40682023
Create Date: 2025-09-29 19:57:58.572623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '281cb7424067'
down_revision: Union[str, None] = '57ac40682023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix sessions table primary key autoincrement."""
    # SQLite doesn't support ALTER TABLE for primary key changes
    # We need to recreate the table with proper structure

    # Step 1: Create new sessions table with proper primary key
    op.create_table('sessions_new',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('started_at', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('paused_at', sa.DateTime()),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('problems_reviewed', sa.Integer(), default=0),
        sa.Column('total_time_seconds', sa.Integer(), default=0),
        sa.Column('max_duration_minutes', sa.Integer(), default=45),
    )

    # Step 2: Copy existing data (excluding rows with NULL ids)
    op.execute("""
        INSERT INTO sessions_new (id, started_at, completed_at, paused_at, status, problems_reviewed, total_time_seconds, max_duration_minutes)
        SELECT id, started_at, completed_at, paused_at, status, problems_reviewed,
               COALESCE(total_time_seconds, 0), COALESCE(max_duration_minutes, 45)
        FROM sessions
        WHERE id IS NOT NULL
    """)

    # Step 3: Drop old table and rename new one
    op.drop_table('sessions')
    op.rename_table('sessions_new', 'sessions')


def downgrade() -> None:
    """Downgrade schema - revert to old sessions table structure."""
    # Create old table structure (without proper primary key)
    op.create_table('sessions_old',
        sa.Column('id', sa.Integer()),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('paused_at', sa.DateTime()),
        sa.Column('status', sa.String(20)),
        sa.Column('problems_reviewed', sa.Integer()),
        sa.Column('total_time_seconds', sa.Integer()),
        sa.Column('max_duration_minutes', sa.Integer()),
    )

    # Copy data back
    op.execute("""
        INSERT INTO sessions_old SELECT * FROM sessions
    """)

    # Replace table
    op.drop_table('sessions')
    op.rename_table('sessions_old', 'sessions')
