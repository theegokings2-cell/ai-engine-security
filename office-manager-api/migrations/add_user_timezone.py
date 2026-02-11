"""Add timezone column to users table

Revision ID: add_user_timezone
Revises: 
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_timezone'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add timezone column with default 'UTC'
    op.add_column('users', sa.Column('timezone', sa.String(50), server_default='UTC', nullable=False))
    
    # Update existing users to have UTC timezone
    op.execute("UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL")


def downgrade():
    op.drop_column('users', 'timezone')
