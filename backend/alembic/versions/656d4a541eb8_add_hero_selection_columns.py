"""Add hero selection columns

Revision ID: 656d4a541eb8
Revises: 
Create Date: 2026-01-07 02:16:03.764515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '656d4a541eb8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('matches', sa.Column('selected_hero_name', sa.String(100), nullable=True))
    op.add_column('matches', sa.Column('selected_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('matches', 'selected_at')
    op.drop_column('matches', 'selected_hero_name')
