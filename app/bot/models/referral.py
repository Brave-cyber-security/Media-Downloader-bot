from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bot.models.users import User

from app.core.models import BaseModelWithData
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Referral(BaseModelWithData):
    __tablename__ = "referrals"
    tg_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.tg_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="References users.tg_id",
    )
    invited_tg_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, doc="Telegram ID of the user who referred"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="referral",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Referral tg_id={self.tg_id!r}"
