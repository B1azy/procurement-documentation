"""Уточняющие вопросы агента"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.purchase import Purchase


class QuestionAnswerSource:
    """Источник ответа. Константы, а не Enum, чтобы не плодить миграции

    USER — пользователь ответил по существу
    DONT_KNOW — пользователь ответил «не знаю»; типовое значение подставит LLM при генерации ТЗ и пометит в assumptions"""

    USER = "user_defined"
    DONT_KNOW = "dont_know"


class PurchaseQuestion(Base):
    __tablename__ = "purchase_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        index=True,
    )

    # не более 3 раундов. Раунд 1 — типовые+LLM
    # раунды 2–3 — только LLM по ответам предыдущего раунда
    round: Mapped[int] = mapped_column(Integer, default=1, index=True)
    order: Mapped[int] = mapped_column(Integer)  # порядок внутри раунда

    text: Mapped[str] = mapped_column(Text)
    # подсказка и варианты ответа для сложных вопросов
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list] = mapped_column(JSON, default=list)

    # answer=None + answer_source="dont_know" — валидное состояние
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # answered_at is not None — вопрос закрыт. Генерация ТЗ требует, чтобы все вопросы были закрыты
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    purchase: Mapped["Purchase"] = relationship(back_populates="questions")
