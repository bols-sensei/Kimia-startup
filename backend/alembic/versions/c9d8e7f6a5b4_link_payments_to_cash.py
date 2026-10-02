"""link payments to cash transactions, add voided_at

Revision ID: c9d8e7f6a5b4
Revises: b7c1d2e3f405
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d8e7f6a5b4'
down_revision = 'b7c1d2e3f405'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('cash_transaction_id', sa.Integer(), nullable=True))
    op.add_column('payments', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_payments_cash_transaction', 'payments', 'cash_transactions',
        ['cash_transaction_id'], ['id'], ondelete='SET NULL',
    )
    op.create_unique_constraint('uq_payments_cash_transaction', 'payments', ['cash_transaction_id'])


def downgrade() -> None:
    op.drop_constraint('uq_payments_cash_transaction', 'payments', type_='unique')
    op.drop_constraint('fk_payments_cash_transaction', 'payments', type_='foreignkey')
    op.drop_column('payments', 'voided_at')
    op.drop_column('payments', 'cash_transaction_id')
