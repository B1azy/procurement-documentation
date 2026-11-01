"""Экспорт ТЗ в DOCX через docxtpl (FR-G-02). Шаблон — Jinja2 внутри Word."""

import io
from pathlib import Path

from docxtpl import DocxTemplate

from app.schemas.specifications import TechnicalSpecification

# Шаблон лежит в <корень проекта>/templates/, а не внутри app/,
# чтобы его можно было править без перезапуска Python-кода.
TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "templates"
    / "specification_template.docx"
)

# Человекочитаемые подписи для enum'ов из schemas/specifications.py.
# В шаблоне используем {{ v.basis_label }} вместо технического "agent_estimate".
SOURCE_LABELS = {
    "user_defined": "указано пользователем",
    "agent_estimate": "оценка агента",
    "typical_assumption": "типовое допущение",
}


def render_specification(spec: TechnicalSpecification, version: int) -> io.BytesIO:
    """Рендерит DOCX из шаблона и данных ТЗ. Возвращает байтовый поток, готовый к отдаче.

    Кидает FileNotFoundError, если шаблон не создан (см. README).
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Шаблон DOCX не найден: {TEMPLATE_PATH}. "
            "Создайте его по инструкции в README."
        )

    # mode="json" — чтобы datetime/UUID/enum не сломали рендер; docxtpl ждёт примитивы.
    context = spec.model_dump(mode="json")
    context["version"] = version

    # Обогащаем контекст: переводим enum'ы в читаемый русский текст.
    # Делаем это здесь, а не в Pydantic-схеме, чтобы не тащить локализацию в контракт API.
    for volume in context["volumes"]:
        volume["basis_label"] = SOURCE_LABELS.get(volume["basis"], volume["basis"])
    for assumption in context["assumptions"]:
        assumption["source_label"] = SOURCE_LABELS.get(
            assumption["source"], assumption["source"]
        )

    if context["materials"].get("notes"):
        context["materials"]["notes"] = (
            context["materials"]["notes"]
            .replace("(user_defined)", "")
            .replace("(typical_assumption)", "")
            .strip()
        )
    if context["quality"].get("notes"):
        context["quality"]["notes"] = (
            context["quality"]["notes"]
            .replace("(user_defined)", "")
            .replace("(typical_assumption)", "")
            .strip()
        )

    doc = DocxTemplate(str(TEMPLATE_PATH))
    doc.render(context)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
