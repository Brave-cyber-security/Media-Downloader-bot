from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bot.models.statistics import Statistics
    from app.bot.models.referral import Referral

from app.core.models.base import BaseModelWithData
from sqlalchemy import BigInteger, Boolean, String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property


class User(BaseModelWithData):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False, unique=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(
        String(32), nullable=True, unique=True, index=True
    )
    language_code: Mapped[str | None] = mapped_column(
        String(8), nullable=True, default=None
    )

    is_tg_premium: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    last_active: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        onupdate=datetime.now,
        default=datetime.now,
    )

    referred_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, default=None, index=True
    )

    subscription_expiry: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, index=True
    )

    # one-to-one relationship to Statistics
    statistics: Mapped["Statistics"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    # one-to-one relationship to Referral
    referral: Mapped["Referral"] = relationship(
        "Referral", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tokens: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False, index=True
    )
    free_requests_left: Mapped[int] = mapped_column(
        BigInteger, default=10, nullable=False
    )

    @hybrid_property
    def full_name(self) -> str:
        # hybrid_property lets you filter/query on full_name too if needed
        return f"{self.first_name} {self.last_name or ''}".strip()

    def __repr__(self) -> str:
        return f"<User tg_id={self.tg_id!r} username={self.username!r}>"

    def get_referral_link(self, bot_username: str) -> str:
        return f"https://t.me/{bot_username}?start=" + str(self.tg_id)

    def is_active(self) -> bool:
        return self.last_active > datetime.now() - timedelta(days=30)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tg_id": self.tg_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "language_code": self.language_code,
            "is_tg_premium": self.is_tg_premium,
            "free_requests_left": self.free_requests_left,
            "last_active": self.last_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_premium(self) -> bool:
        return self.subscription_expiry and self.subscription_expiry >= datetime.now()

    def set_premium(self) -> None:
        setattr(self, "subscription_expiry", datetime.now() + timedelta(days=30))
