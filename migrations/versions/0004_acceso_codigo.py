"""Link LATIA accounts to verified email identities."""

import sqlalchemy as sa
from alembic import op

revision = "0004_acceso_codigo"
down_revision = "0003_rangos"


def upgrade():
    op.add_column("accounts", sa.Column("auth_user_id", sa.Uuid()), schema="latia")
    op.create_unique_constraint("accounts_auth_user_id_key", "accounts", ["auth_user_id"], schema="latia")
    op.alter_column("accounts", "password_hash", nullable=True, schema="latia")
    op.create_check_constraint(
        "ck_accounts_access", "accounts", "password_hash IS NOT NULL OR auth_user_id IS NOT NULL", schema="latia",
    )


def downgrade():
    op.alter_column("accounts", "password_hash", nullable=False, schema="latia")
    op.drop_constraint("ck_accounts_access", "accounts", type_="check", schema="latia")
    op.drop_constraint("accounts_auth_user_id_key", "accounts", type_="unique", schema="latia")
    op.drop_column("accounts", "auth_user_id", schema="latia")
