from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Index, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "latia"


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64))
    session_version: Mapped[int] = mapped_column(server_default="0")
    profile_photo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (
        CheckConstraint(
            "systolic BETWEEN 1 AND 999 AND diastolic BETWEEN 1 AND 999 "
            "AND pulse BETWEEN 1 AND 999 AND systolic > diastolic",
            name="ck_readings_values",
        ),
        Index("ix_readings_account_time_id", "account_id", "measured_at", "id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("latia.accounts.id", ondelete="CASCADE"))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    systolic: Mapped[int]
    diastolic: Mapped[int]
    pulse: Mapped[int]
    note: Mapped[str] = mapped_column(String(500))
