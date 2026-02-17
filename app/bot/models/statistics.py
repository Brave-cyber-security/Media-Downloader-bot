from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bot.models.users import User
from app.core.models import BaseModel
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Statistics(BaseModel):
    __tablename__ = "statistics"

    tg_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.tg_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="References users.tg_id",
    )
    from_text: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_voice: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_youtube: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_tiktok: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_like: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_snapchat: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_instagram: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_twitter: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    from_video: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    user: Mapped[User] = relationship(
        back_populates="statistics", uselist=False, lazy="selectin"
    )

    def add_one(self, field: str) -> bool:
        """
        Fields:
        - user_id: ID of the user
        - from_text: Count of text messages sent by the user
        - from_voice: Count of voice messages sent by the user
        - from_youtube: Count of YouTube links shared by the user
        - from_tiktok: Count of TikTok links shared by the user
        - from_like: Count of likes given by the user
        - from_snapchat: Count of Snapchat links shared by the user
        - from_instagram: Count of Instagram links shared by the user
        - from_twitter: Count of Twitter links shared by the user
        - from_video: Count of videos shared by the user
        """
        if hasattr(self, field):
            current_value = getattr(self, field, 0)
            setattr(self, field, current_value + 1)
            return True
        return False

    def __repr__(self) -> str:
        return f"<Statistics tg_id={self.tg_id!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tg_id": self.tg_id,
            "from_text": self.from_text,
            "from_voice": self.from_voice,
            "from_youtube": self.from_youtube,
            "from_tiktok": self.from_tiktok,
            "from_like": self.from_like,
            "from_snapchat": self.from_snapchat,
            "from_instagram": self.from_instagram,
            "from_twitter": self.from_twitter,
            "from_video": self.from_video,
        }
