"""Store the school names on a game.

Revision ID: 0002_game_schools
Revises: 0001_initial
Create Date: 2026-11-11

Fresh databases already have these columns because revision 0001 creates the
tables from the current models. This revision adds the columns only when an
older database is upgraded.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0002_game_schools"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("games")}
    if "home_school" not in columns:
        op.add_column("games", sa.Column("home_school", sa.String(length=200), nullable=True))
    if "away_school" not in columns:
        op.add_column("games", sa.Column("away_school", sa.String(length=200), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("games")}
    if "away_school" in columns:
        op.drop_column("games", "away_school")
    if "home_school" in columns:
        op.drop_column("games", "home_school")
