import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.question import PurchaseQuestion
    from app.models.specification import Specification
    from app.models.user import User


class PurchaseStatus(str, Enum):
    DRAFT = "draft"
    # analysis.needs_questions=true, вопросы сгенерированы, ждём ответов
    QUESTIONS_PENDING = "questions_pending"
    # analysis.needs_questions=false ИЛИ все вопросы отвечены — можно генерировать ТЗ
    READY_FOR_SPEC = "ready_for_spec"
    SPEC_DRAFTED = "spec_drafted"
    EXPORTED = "exported"


class PurchaseType(str, Enum):
    WORK = "work"  # работа: ремонт кровли, замена окна
    SERVICE = "service"  # услуга: уборка, охрана
    GOODS = "goods"  # товар: закупка материалов


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    structured_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default=PurchaseStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Тип предмета закупки, определяется анализом (work/service/goods)
    purchase_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Результат анализа: {"work_type", "purchase_type", "completeness",
    # "needs_questions", "missing_info", "reasoning"}
    # JSON, а не колонки — структура может расширяться без миграции
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="purchases")
    specifications: Mapped[list["Specification"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )
    questions: Mapped[list["PurchaseQuestion"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )
