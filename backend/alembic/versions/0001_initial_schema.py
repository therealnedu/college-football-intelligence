"""Initial schema from the SQLAlchemy models.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-10

The model metadata is the single schema definition. Alembic applies it so a
later hand-written migration cannot silently diverge from the models in phase 1.
"""

from typing import Sequence, Union

from alembic import op

from app import models  # noqa: F401
from app.db import Base

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
