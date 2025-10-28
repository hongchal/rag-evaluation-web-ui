"""Add prompt templates table

Revision ID: 20251028_add_prompt_templates
Revises: 20251028_add_chat_sessions
Create Date: 2025-10-28 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_prompt_templates'
down_revision = 'add_chat_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create prompt_templates table."""
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompt_templates_id'), 'prompt_templates', ['id'], unique=False)


def downgrade() -> None:
    """Drop prompt_templates table."""
    op.drop_index(op.f('ix_prompt_templates_id'), table_name='prompt_templates')
    op.drop_table('prompt_templates')

