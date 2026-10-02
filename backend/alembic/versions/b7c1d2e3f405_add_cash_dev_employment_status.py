"""add cash ledger, dev memberships, employment_status

Revision ID: b7c1d2e3f405
Revises: a1aef567664a
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c1d2e3f405'
down_revision = 'a1aef567664a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('employment_status', sa.String(length=20), nullable=False, server_default='ACTIVE'))

    op.create_table(
        'cash_closings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('closing_date', sa.Date(), nullable=False),
        sa.Column('opening_balance', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_in', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_out', sa.Numeric(12, 2), nullable=False),
        sa.Column('closing_balance', sa.Numeric(12, 2), nullable=False),
        sa.Column('counted_balance', sa.Numeric(12, 2), nullable=True),
        sa.Column('difference', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('closed_by', sa.Integer(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['closed_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('closing_date'),
    )
    op.create_table(
        'cash_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=30), nullable=False),
        sa.Column('direction', sa.String(length=3), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('project_service_id', sa.Integer(), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('closing_id', sa.Integer(), nullable=True),
        sa.Column('reversal_of_id', sa.Integer(), nullable=True),
        sa.Column('reversal_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_cash_amount_positive'),
        sa.CheckConstraint("direction in ('IN','OUT')", name='ck_cash_direction'),
        sa.ForeignKeyConstraint(['project_service_id'], ['project_services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closing_id'], ['cash_closings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reversal_of_id'], ['cash_transactions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference'),
        sa.UniqueConstraint('reversal_of_id'),
    )
    op.create_table(
        'dev_memberships',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=10), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("level in ('INTERNAL','MEMBER')", name='ck_dev_level'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('dev_memberships')
    op.drop_table('cash_transactions')
    op.drop_table('cash_closings')
    op.drop_column('users', 'employment_status')
