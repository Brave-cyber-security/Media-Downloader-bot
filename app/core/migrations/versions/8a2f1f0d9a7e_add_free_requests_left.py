"""add free requests left to users

Revision ID: 8a2f1f0d9a7e
Revises: 950ae4d6d476
Create Date: 2026-02-17 16:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a2f1f0d9a7e"
down_revision: Union[str, None] = "950ae4d6d476"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "free_requests_left",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("10"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "free_requests_left")
