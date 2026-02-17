from sqlalchemy.sql.sqltypes import BigInteger

from app.core.models import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Backup(BaseModel):
    __tablename__ = "backup"

    url: Mapped[str] = mapped_column(String, nullable=False, index=True)

    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    def __repr__(self):
        return f"Backup(url={self.url}, message_id={self.message_id})"
