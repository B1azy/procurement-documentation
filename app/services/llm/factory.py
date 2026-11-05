"""Фабрика LLM-клиентов. Единственное место, где решается, к какому провайдеру идти.

При добавлении провайдера:
1. Создать app/services/llm/<provider>_client.py с методом generate_structured.
2. Добавить case в match ниже.
3. Указать LLM_PROVIDER=<provider> в .env.
Сервисы (spec_generator, question_service) не меняются.
"""

from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.gigachat_client import GigaChatClient
from app.services.llm.ollama_client import OllamaClient


def get_llm_client() -> LLMClient:
    """Возвращает клиент выбранного провайдера. Кидает ValueError при неизвестном значении."""
    match settings.llm_provider:
        case "ollama":
            return OllamaClient()
        case "gigachat":
            return GigaChatClient()
        case _:
            raise ValueError(
                f"Неизвестный LLM_PROVIDER: {settings.llm_provider!r}. "
                "Допустимые: ollama."
            )
