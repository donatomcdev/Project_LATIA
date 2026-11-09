"""Add private profile photos and a session version for password changes."""

import sqlalchemy as sa
from alembic import op

revision = "0002_perfil"
down_revision = "0001_diario"


def upgrade():
    op.add_column(
        "accounts",
        sa.Column("session_version", sa.Integer(), server_default="0", nullable=False),
        schema="latia",
    )
    op.add_column("accounts", sa.Column("profile_photo", sa.LargeBinary()), schema="latia")


def downgrade():
    op.drop_column("accounts", "profile_photo", schema="latia")
    op.drop_column("accounts", "session_version", schema="latia")
