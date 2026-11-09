"""Create the private LATIA journal tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_diario"
down_revision = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        schema="latia",
    )
    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("latia.accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("systolic", sa.Integer(), nullable=False),
        sa.Column("diastolic", sa.Integer(), nullable=False),
        sa.Column("pulse", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.CheckConstraint(
            "systolic BETWEEN 1 AND 999 AND diastolic BETWEEN 1 AND 999 "
            "AND pulse BETWEEN 1 AND 999 AND systolic > diastolic",
            name="ck_readings_values",
        ),
        schema="latia",
    )
    op.create_index("ix_readings_account_time_id", "readings", ["account_id", "measured_at", "id"], schema="latia")


def downgrade():
    op.drop_table("readings", schema="latia")
    op.drop_table("accounts", schema="latia")
