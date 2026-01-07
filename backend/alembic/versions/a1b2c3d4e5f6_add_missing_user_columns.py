"""Add missing user columns

Revision ID: a1b2c3d4e5f6
Revises: 672850d57be6
Create Date: 2026-01-07 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '672850d57be6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    if 'steam_id' not in columns:
        op.add_column('users', sa.Column('steam_id', sa.String(length=50), nullable=True))
        op.create_unique_constraint(None, 'users', ['steam_id'])
        
    if 'stripe_customer_id' not in columns:
        op.add_column('users', sa.Column('stripe_customer_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    if 'stripe_customer_id' in columns:
        op.drop_column('users', 'stripe_customer_id')
        
    if 'steam_id' in columns:
        op.drop_constraint('users_steam_id_key', 'users', type_='unique')
        op.drop_column('users', 'steam_id')
