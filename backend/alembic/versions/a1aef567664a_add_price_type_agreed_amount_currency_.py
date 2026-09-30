"""add price_type, agreed_amount, currency, reference, event_date, event_location

Revision ID: a1aef567664a
Revises: 
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1aef567664a'
down_revision: Union[str, None] = '2eaf395a08e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # services : ajouter price_type
    # ------------------------------------------------------------------ #
    op.add_column(
        'services',
        sa.Column('price_type', sa.String(length=20), nullable=False, server_default='FIXE')
    )

    # ------------------------------------------------------------------ #
    # requests : ajouter les nouvelles colonnes
    # ------------------------------------------------------------------ #

    # 1. reference (nullable d'abord pour remplir les données existantes)
    op.add_column(
        'requests',
        sa.Column('reference', sa.String(length=50), nullable=True)
    )

    # 2. Remplir les références existantes avec une valeur temporaire
    op.execute(
        "UPDATE requests SET reference = 'DEM-' || EXTRACT(YEAR FROM created_at)::text || '-' || LPAD(id::text, 4, '0') WHERE reference IS NULL"
    )

    # 3. Rendre la colonne NOT NULL
    op.alter_column('requests', 'reference', nullable=False)

    # 4. Créer la contrainte unique
    op.create_unique_constraint('uq_requests_reference', 'requests', ['reference'])

    # 5. Ajouter les autres colonnes
    op.add_column(
        'requests',
        sa.Column('agreed_amount', sa.Numeric(precision=12, scale=2), nullable=True)
    )
    op.add_column(
        'requests',
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD')
    )
    op.add_column(
        'requests',
        sa.Column('event_date', sa.Date(), nullable=True)
    )
    op.add_column(
        'requests',
        sa.Column('event_location', sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # requests : supprimer les colonnes
    # ------------------------------------------------------------------ #
    op.drop_column('requests', 'event_location')
    op.drop_column('requests', 'event_date')
    op.drop_column('requests', 'currency')
    op.drop_column('requests', 'agreed_amount')
    op.drop_constraint('uq_requests_reference', 'requests', type_='unique')
    op.drop_column('requests', 'reference')

    # ------------------------------------------------------------------ #
    # services : supprimer price_type
    # ------------------------------------------------------------------ #
    op.drop_column('services', 'price_type')