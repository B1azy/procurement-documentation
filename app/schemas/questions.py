"""Схемы уточняющего диалога и перегенерации раздела"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionItem(BaseModel):
    """Один вопрос. Используется и как схема ответа LLM, и как элемент QuestionSet

    options — варианты ответа; пользователь может выбрать или ввести свой текст
    Пустой список — вопрос открытый
    """

    text: str = Field(description="Вопрос простым языком, без жаргона")
    hint: str | None = Field(default=None, description="Подсказка для сложного вопроса")
    options: list[str] = Field(
        default_factory=list, description="Варианты ответа (может быть пусто)"
    )


class QuestionSet(BaseModel):
    """Набор вопросов одного раунда. max_length=7"""

    questions: list[QuestionItem] = Field(default_factory=list, max_length=7)


class QuestionRead(BaseModel):
    """Ответ API. answered_at=None — вопрос ещё не закрыт"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    round: int
    order: int
    text: str
    hint: str | None
    options: list[str]
    answer: str | None
    answer_source: str | None
    answered_at: datetime | None


class QuestionAnswerIn(BaseModel):
    """Ответ на один вопрос. dont_know=True

    Ровно одно из полей должно быть задано: либо answer, либо dont_know=True
    Проверка — в сервисе, а не в Pydantic
    """

    answer: str | None = Field(default=None, max_length=2000)
    dont_know: bool = False


class BatchAnswerItem(QuestionAnswerIn):
    """Элемент batch-ответа: тот же QuestionAnswerIn + id вопроса"""

    question_id: UUID


class BatchAnswerIn(BaseModel):
    """Batch-ответ на несколько вопросов за один запрос

    Атомарность: если хотя бы один вопрос не найден или уже отвечен —
    весь batch отклоняется, ни один ответ не применяется
    """

    answers: list[BatchAnswerItem] = Field(min_length=1)


class SectionRegenerateIn(BaseModel):
    """Перегенерация одного раздела ТЗ"""

    section: str = Field(
        description="Имя раздела: general_info, materials, quality, ..."
    )
    instruction: str = Field(
        min_length=1,
        max_length=2000,
        description="Что именно изменить в разделе",
    )
