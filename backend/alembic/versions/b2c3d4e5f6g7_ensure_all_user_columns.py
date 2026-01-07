"""Ensure all user columns exist

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08 00:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    # Check and add 'tier'
    if 'tier' not in columns:
        op.add_column('users', sa.Column('tier', sa.String(length=20), server_default='FREE', nullable=False))
        
    # Check and add 'is_active'
    if 'is_active' not in columns:
        op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
        
    # Check and add 'created_at'
    if 'created_at' not in columns:
        op.add_column('users', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
        
    # Check and add 'updated_at'
    if 'updated_at' not in columns:
        op.add_column('users', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    if 'updated_at' in columns:
        op.drop_column('users', 'updated_at')
        
    if 'created_at' in columns:
        op.drop_column('users', 'created_at')
        
    if 'is_active' in columns:
        op.drop_column('users', 'is_active')
        
    if 'tier' in columns:
        op.drop_column('users', 'tier')
