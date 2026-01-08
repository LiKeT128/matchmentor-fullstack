"""Add source column to matches

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-09 00:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source column to track data origin (opendota/clarity)."""
    op.add_column('matches', sa.Column('source', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove source column."""
    op.drop_column('matches', 'source')
