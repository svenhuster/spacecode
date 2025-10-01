"""Baseline schema migration

Revision ID: 001_baseline_schema
Revises:
Create Date: 2025-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_baseline_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create all tables with current schema."""

    # Create problems table
    op.create_table('problems',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('url', sa.String(500), unique=True, nullable=False),
        sa.Column('slug', sa.String(200)),
        sa.Column('title', sa.String(300)),
        sa.Column('number', sa.Integer()),
        sa.Column('difficulty', sa.String(20)),
        sa.Column('tags', sa.Text()),
        sa.Column('description', sa.Text()),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('is_active', sa.Boolean(), default=True),
    )

    # Create problem_stats table
    op.create_table('problem_stats',
        sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id'), primary_key=True),
        sa.Column('easiness_factor', sa.Float(), default=2.5),
        sa.Column('interval_hours', sa.Float(), default=1.0),
        sa.Column('repetitions', sa.Integer(), default=0),
        sa.Column('next_review', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('last_rating', sa.Integer()),
        sa.Column('total_reviews', sa.Integer(), default=0),
        sa.Column('average_rating', sa.Float()),
        sa.Column('last_reviewed', sa.DateTime()),
    )

    # Create sessions table with proper schema
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('started_at', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('paused_at', sa.DateTime()),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('problems_reviewed', sa.Integer(), default=0),
        sa.Column('total_time_seconds', sa.Integer(), default=0),
        sa.Column('max_duration_minutes', sa.Integer(), default=45),
    )

    # Create reviews table
    op.create_table('reviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('time_spent_seconds', sa.Integer()),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id')),
    )


def downgrade() -> None:
    """Downgrade schema - Drop all tables."""
    op.drop_table('reviews')
    op.drop_table('sessions')
    op.drop_table('problem_stats')
    op.drop_table('problems')