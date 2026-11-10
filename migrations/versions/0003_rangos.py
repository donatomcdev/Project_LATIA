"""Store personal blood pressure ranges."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_rangos"
down_revision = "0002_perfil"


def upgrade():
    op.add_column("accounts", sa.Column("pressure_ranges", JSONB()), schema="latia")


def downgrade():
    op.drop_column("accounts", "pressure_ranges", schema="latia")
