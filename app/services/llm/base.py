"""Интерфейс LLM-клиента. Сервисы зависят от этого Protocol, а не от конкретного провайдера.

Смысл: при переходе с Ollama на GigaChat/OpenAI меняется только реализация
и фабрика. spec_generator и question_service не трогаются.
"""

from typing import Protocol, Type, TypeVar

from pydantic import BaseModel

# T ограничен BaseModel: клиент обязан вернуть валидированный Pydantic-объект, а не сырой текст
T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> T:
        """Отправляет промпт модели и возвращает валидированный Pydantic-объект.

        Кидает ValueError, если модель вернула невалидный JSON/не соответствующую схему.
        Конкретные HTTP-ошибки провайдера (таймауты, 5xx) могут пробрасываться как есть.
        """
        ...
