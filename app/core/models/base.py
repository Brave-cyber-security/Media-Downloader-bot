from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func, DateTime
from datetime import datetime

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    def __repr__(self):
        return f"Repr <{self.__str__()}>"

    def __str__(self):
        return f"{self.__class__.__name__}"

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                if value is None:
                    continue
                setattr(self, key, value)
        setattr(self, "updated_at", datetime.now())
        return self


class BaseModelWithData(BaseModel):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=datetime.now, nullable=True
    )
