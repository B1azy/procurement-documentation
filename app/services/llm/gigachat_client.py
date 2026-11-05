import base64
from typing import Type, TypeVar

from gigachat import GigaChat
from gigachat.models import Chat, ChatCompletionRequest, Messages, MessagesRole
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class GigaChatClient:
    """Клиент GigaChat, реализующий интерфейс LLMClient."""

    def __init__(self):
        self._client = GigaChat(
            credentials=settings.gigachat_credentials,
            model=settings.gigachat_model,
            verify_ssl_certs=settings.gigachat_verify_ssl_certs,
        )

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> T:
        # Формируем итоговый промпт
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            # В новом контракте используем achat.parse с параметром response_format
            completion, parsed = await self._client.achat.parse(
                full_prompt,
                response_format=response_model,
                strict=True,
            )
            return parsed
        except ValidationError as exc:
            raise ValueError(f"GigaChat вернул невалидный JSON: {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Ошибка при запросе к GigaChat: {exc}") from exc

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        """Анализ изображения через Vision (старый контракт с Chat + Messages)."""

        # 1. Загружаем файл и получаем его ID
        file = self._client.upload_file(("image.jpg", image_bytes, "image/jpeg"))
        file_id = file.id_

        # 2. Создаём сообщение с вложением (здесь используется Messages, а не ChatMessage)
        message = Messages(
            role=MessagesRole.USER,
            content=prompt,
            attachments=[file_id],
        )

        # 3. Оборачиваем в Chat (старый контракт)
        chat = Chat(
            messages=[message],
            model=settings.gigachat_model,
        )

        # 4. Отправляем запрос (корневой метод achat, не achat.create)
        response = await self._client.achat(chat)

        # 5. Извлекаем текст ответа (в старом контракте content — это строка)
        return response.choices[0].message.content
