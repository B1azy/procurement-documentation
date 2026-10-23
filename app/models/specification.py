import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.purchase import Purchase


class Specification(Base):
    __tablename__ = "specifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSON)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    purchase: Mapped["Purchase"] = relationship(back_populates="specifications")
    assumptions: Mapped[list["SpecAssumption"]] = relationship(
        back_populates="specification", cascade="all, delete-orphan"
    )


class SpecAssumption(Base):
    __tablename__ = "spec_assumptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    specification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("specifications.id", ondelete="CASCADE"),
        index=True,
    )
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32))
    requires_check: Mapped[bool] = mapped_column(Boolean, default=True)

    specification: Mapped["Specification"] = relationship(back_populates="assumptions")
