"""Настройки приложения, читаются из .env (NFR-04: секреты в переменных окружения)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore" — чтобы в .env могли лежать переменные других сервисов (Docker и т.п.)
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "FastAPI Project"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi"

    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- LLM ---
    # Провайдеры для LLM. Например, "ollama"
    llm_provider: str = "ollama"

    # Модель по умолчанию
    llm_model: str = "qwen3.5:4b"

    # Разные модели под разные задачи (необязательно)
    llm_model_questions: str | None = None
    llm_model_spec: str | None = None

    # Контекстное окно для Ollama. Для агентных задач нужно ≥32K,
    # иначе системный промпт со схемой обрезается
    llm_num_ctx: int = 65536

    # Базовый URL Ollama
    ollama_base_url: str = "http://localhost:11434"


settings = Settings()
