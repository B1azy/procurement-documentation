"""Адаптер к локальной Ollama. Реализует интерфейс LLMClient.

Ollama принимает JSON Schema через параметр format и сама заставляет модель
вернуть JSON ровно этой формы. Это надёжнее, чем «просить JSON» в промпте.
"""

from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    """Клиент Ollama. Не хранит состояние — можно создавать на каждый запрос."""

    def __init__(self, base_url: str | None = None, num_ctx: int | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.num_ctx = num_ctx or settings.llm_num_ctx

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> T:
        """Возвращает Pydantic-объект. model по умолчанию — settings.llm_model."""
        target_model = model or settings.llm_model

        # model_json_schema() отдаёт схему, которую Ollama использует как ограничение для генераци
        schema = response_model.model_json_schema()

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "options": {
                # Для агентных задач ≥32K: иначе системный промпт + схема обрезаются
                "num_ctx": self.num_ctx,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()

        raw = response.json()["response"]

        try:
            # Валидация ответа — единая точка контроля. Если модель вернула
            # не то, сервисы получают ValueError и превращают в 502.
            return response_model.model_validate_json(raw)
        except ValidationError as exc:
            raise ValueError(
                f"Модель вернула невалидный JSON: {exc}\nОтвет: {raw}"
            ) from exc
