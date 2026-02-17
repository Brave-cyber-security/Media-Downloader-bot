from app.core.models import BaseModelWithData
from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column


class Channel(BaseModelWithData):
    __tablename__ = "channels"
    name: Mapped[str] = mapped_column(String, nullable=False)
    link: Mapped[str | None] = mapped_column(String, nullable=False, unique=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
