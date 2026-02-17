from sqlalchemy.sql.sqltypes import BigInteger, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class AdminRequirements(BaseModel):
    __tablename__ = "admin_requirements"

    referral_count_for_free_month: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=10
    )
    premium_price: Mapped[float] = mapped_column(Float, nullable=False, default="2.99")

    def __repr__(self) -> str:
        return f"<AdminRequirements token_per_referral={self.referral_count_for_free_month!r}>"
