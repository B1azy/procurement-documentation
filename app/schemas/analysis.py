"""Схема результата анализа закупки (определение типа, вида, полноты)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PurchaseAnalysis(BaseModel):
    """Результат анализа. Используется и как схема ответа LLM, и как ответ API."""

    work_type: str = Field(
        description="Вид работ/услуги/товара, например 'кровля', 'замена окна'"
    )
    purchase_type: Literal["work", "service", "goods"] = Field(
        description="Тип предмета закупки: работа, услуга или товар"
    )
    completeness: Literal["low", "medium", "high"] = Field(
        description="Полнота описания для составления полного ТЗ"
    )
    needs_questions: bool = Field(
        description="Нужны ли уточняющие вопросы (недостаточно данных)"
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="Каких именно сведений не хватает (пусто, если не нужны вопросы)",
    )
    reasoning: str = Field(
        description="Короткое обоснование решения (для отладки и прозрачности)"
    )


class AnalysisRead(BaseModel):
    """Ответ API /analyze."""

    model_config = ConfigDict(from_attributes=True)

    purchase_type: str | None
    analysis: PurchaseAnalysis | None
