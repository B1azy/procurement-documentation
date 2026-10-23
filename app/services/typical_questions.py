"""Типовые уточняющие вопросы по видам работ

Вопросы лежат в YAML
"""

from functools import lru_cache
from pathlib import Path

import yaml

DATA_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "typical_questions.yaml"
)

# Ключевые слова для определения вида работ, ищем в work_type + description. Если ничего не нашли — работаем только через LLM
# Точность ~90% на типичных формулировках («ремонт кровли», «протечка в паркинге»)
WORK_TYPE_KEYWORDS = {
    "кровля": ["кровл", "крыш"],
    "фасад": ["фасад", "облицов", "штукатур"],
    "плитка": ["плитк", "керамогранит", "кафель"],
    "доводчик": ["доводчик"],
    "протечка": ["протечк", "затоплен", "течёт", "течь"],
    "замена окна": ["окн", "окон", "стеклопакет"],
}


@lru_cache(maxsize=1)
def load_typical_questions() -> dict[str, list[dict]]:
    """Читает YAML один раз и кэширует. Если файла нет — пустой словарь

    lru_cache: правки в YAML подхватятся только после перезапуска uvicorn
    """
    if not DATA_PATH.exists():
        return {}
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def detect_work_type(work_type: str | None, description: str) -> str | None:
    """Определяет вид работ по work_type и описанию. None, если не уверены"""
    haystack = f"{work_type or ''} {description}".lower()
    for canonical, keywords in WORK_TYPE_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return canonical
    return None


def get_questions_for_work_type(work_type: str | None) -> list[dict]:
    """Возвращает generic + вопросы вида работ, дедуп по тексту

    Порядок: сначала generic (общие), затем специфичные. Если вид не определён — только generic
    """
    data = load_typical_questions()
    result = list(data.get("generic", []))
    if work_type and work_type in data:
        result.extend(data[work_type])

    seen: set[str] = set()
    unique: list[dict] = []
    for q in result:
        text = (q.get("text") or "").strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(q)
    return unique
