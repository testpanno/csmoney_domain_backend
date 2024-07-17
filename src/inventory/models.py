from database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, JSON, DateTime
from sqlalchemy.sql import func

class Inventory(Base):
    __tablename__ = 'inventory'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    steam_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    skins: Mapped[dict] = mapped_column(JSON)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
