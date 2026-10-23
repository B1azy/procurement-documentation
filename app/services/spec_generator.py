"""Генерация ТЗ, перегенерация раздела и ручная правка"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.purchase import Purchase, PurchaseStatus
from app.models.question import PurchaseQuestion
from app.models.specification import SpecAssumption, Specification
from app.schemas.specifications import TechnicalSpecification
from app.services import analysis_service
from app.services.llm.factory import get_llm_client

SYSTEM_PROMPT = """Ты — эксперт по подготовке технических заданий (ТЗ) на подрядные работы и услуги.

Заполни все 13 разделов ТЗ на основе описания закупки и ответов пользователя на уточняющие вопросы.

ЖЁСТКИЕ ПРАВИЛА:
1. НЕ выдумывай номера и названия ГОСТ, СП, СНиП. Если не уверен — оставь список нормативных ссылок пустым. Лучше пусто, чем выдуманная ссылка.
2. Если пользователь не указал объём работы — оцени его, поставь basis = "agent_estimate", а в basis_note поясни, на чём основана оценка (фото, размеры из описания, типовое значение).
3. Если в блоке «Пользователь не знает ответов» перечислены темы — подставь типовые значения и добавь их в assumptions с source = "typical_assumption" и requires_check = true.
4. Всё, что взято из описания или ответов пользователя — basis = "user_defined".
5. Критерии приёмки должны быть измеримыми: допуски, методы испытаний, акты.
6. В раздел assumptions собери ВСЕ допущения и пункты, требующие проверки пользователем.
7. Отвечай на русском. Верни ТОЛЬКО JSON по схеме, без пояснений.

КРИТИЧНО ВАЖНО:
8. НЕ ОСТАВЛЯЙ ПУСТЫМИ разделы, которые можно заполнить:
   - work_items — всегда перечисли работы в порядке выполнения
   - volumes — всегда указывай объёмы с единицами (шт, кв.м, п.м)
   - materials — всегда перечисли материалы/изделия
   - quality — всегда требования к качеству и технологии
   Если пользователь не указал число — оцени и пометь basis = "agent_estimate".
   Пустой массив допустим ТОЛЬКО для normative_references (пока нет RAG).
9. source = "user_defined" ставь ТОЛЬКО если это буквально есть в описании
   или в ответе пользователя. Всё, что ты добавил сам — typical_assumption
   или agent_estimate.
10. Для пустых строковых полей используй null, а не "" и не "не указан".
"""

# Разделы, которые можно перегенерировать точечно
# Списковые разделы (work_items, volumes, normative_references) тоже можно через обёртку-контейнер
REGENERABLE_SECTIONS = {
    "general_info",
    "object_description",
    "work_items",
    "volumes",
    "materials",
    "quality",
    "normative_references",
    "deadlines",
    "conditions",
    "contractor_requirements",
    "acceptance",
    "warranty",
}

SECTION_REGENERATE_PROMPT = """Ты — эксперт по техническому заданию. Пользователь просит переделать ОДИН раздел ТЗ с дополнительной инструкцией.

ПРАВИЛА:
1. Верни ТОЛЬКО JSON этого раздела, без остальных.
2. Учти инструкцию пользователя и текущее содержимое раздела.
3. Не выдумывай номера и названия ГОСТ, СП, СНиП — если не уверен, оставь список пустым.
4. Если меняешь числа — пометь basis: user_defined / agent_estimate / typical_assumption.
5. Отвечай на русском. Верни ТОЛЬКО JSON по схеме.
"""


async def generate_draft(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> Specification:
    """Генерирует новую версию ТЗ

    Перед генерацией требует, чтобы все раунды вопросов были закрыты
    (включая «не знаю»). Старые версии ТЗ остаются, is_current переключается
    """
    purchase = await _get_owned_purchase(db, user_id, purchase_id)
    await _ensure_ready_for_spec(db, purchase)

    prompt = await _build_prompt(db, purchase)
    client = get_llm_client()
    try:
        spec_content = await client.generate_structured(
            model=settings.llm_model_spec or settings.llm_model,
            prompt=prompt,
            response_model=TechnicalSpecification,
            system_prompt=SYSTEM_PROMPT,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Модель вернула невалидный ответ: {exc}",
        ) from exc

    new_spec = await _save_new_version(
        db, purchase_id, spec_content, assumptions=spec_content.assumptions
    )
    # После всех ответов и генерации — статус "ТЗ готово"
    purchase.status = PurchaseStatus.SPEC_DRAFTED.value
    await db.commit()
    await db.refresh(new_spec)
    await db.refresh(new_spec, attribute_names=["assumptions"])
    return new_spec


async def regenerate_section(
    db: AsyncSession,
    user_id: UUID,
    purchase_id: UUID,
    spec_id: UUID,
    section: str,
    instruction: str,
) -> Specification:
    """Перегенерация одного раздела. Создаёт новую версию всего ТЗ

    Остальные 12 разделов копируются из текущей версии без изменений
    Допущения (assumptions) сохраняются как были — их правят через PATCH
    """
    if section not in REGENERABLE_SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown section: {section}",
        )

    spec = await get_specification(db, user_id, purchase_id, spec_id)
    current = TechnicalSpecification.model_validate(spec.content)
    current_section = getattr(current, section)

    # Для списковых разделов оборачиваем элемент в контейнер,
    # чтобы LLM возвращала JSON-объект (Ollama format ждёт object, не array на верхнем уровне)
    wrapper = _section_wrapper(section)

    prompt = (
        f"Раздел: {section}\n"
        f"Текущее содержимое: {current_section.model_dump_json()}\n"
        f"Инструкция пользователя: {instruction}\n"
        f"Описание закупки: {purchase_description(current)}"
    )
    client = get_llm_client()

    try:
        result = await client.generate_structured(
            model=settings.llm_model_spec or settings.llm_model,
            prompt=prompt,
            response_model=wrapper,
            system_prompt=SECTION_REGENERATE_PROMPT,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Модель вернула невалидный ответ: {exc}",
        ) from exc

    # Достаём новое значение из обёртки: для списковых - result.items,
    # для объектных - result.value
    new_value = getattr(result, "items", None) or getattr(result, "value", None)
    if new_value is None:
        # Теоретически невозможно, но защищает от рассинхрона wrapper и section
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Модель не вернула данные для раздела {section}",
        )

    new_content = current.model_dump(mode="json")
    new_content[section] = (
        [v.model_dump(mode="json") for v in new_value]
        if isinstance(new_value, list)
        else new_value.model_dump(mode="json")
    )

    new_spec = await _save_new_version(
        db,
        purchase_id,
        TechnicalSpecification.model_validate(new_content),
        # Допущения остаются от предыдущей версии — их не трогаем
        assumptions=current.assumptions,
    )
    await db.commit()
    await db.refresh(new_spec)
    await db.refresh(new_spec, attribute_names=["assumptions"])
    return new_spec


async def update_content(
    db: AsyncSession,
    user_id: UUID,
    purchase_id: UUID,
    spec_id: UUID,
    new_content: TechnicalSpecification,
) -> Specification:
    """Ручная правка всего ТЗ. Создаёт новую версию, не перезаписывает старую"""
    await get_specification(db, user_id, purchase_id, spec_id)

    new_spec = await _save_new_version(
        db, purchase_id, new_content, assumptions=new_content.assumptions
    )
    await db.commit()
    await db.refresh(new_spec)
    await db.refresh(new_spec, attribute_names=["assumptions"])
    return new_spec


async def get_specification(
    db: AsyncSession, user_id: UUID, purchase_id: UUID, spec_id: UUID
) -> Specification:
    """Версия ТЗ по id с проверкой владельца. 404, если версия не найдена или чужая"""
    spec = await db.scalar(
        select(Specification)
        .join(Purchase, Specification.purchase_id == Purchase.id)
        .where(
            Specification.id == spec_id,
            Specification.purchase_id == purchase_id,
            Purchase.user_id == user_id,
        )
    )
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Specification not found"
        )
    return spec


async def get_current_specification(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> Specification:
    """Актуальная версия ТЗ (is_current=True). 404, если версий ещё нет"""
    spec = await db.scalar(
        select(Specification)
        .join(Purchase, Specification.purchase_id == Purchase.id)
        .where(
            Specification.purchase_id == purchase_id,
            Specification.is_current.is_(True),
            Purchase.user_id == user_id,
        )
    )
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current specification for this purchase",
        )
    await db.refresh(spec, attribute_names=["assumptions"])
    return spec


async def list_specifications(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> list[Specification]:
    """Все версии ТЗ, новые сверху"""
    result = await db.execute(
        select(Specification)
        .join(Purchase, Specification.purchase_id == Purchase.id)
        .where(
            Specification.purchase_id == purchase_id,
            Purchase.user_id == user_id,
        )
        .order_by(Specification.version.desc())
    )
    return list(result.scalars().all())


# --- Внутренние помощники ---


async def _get_owned_purchase(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> Purchase:
    purchase = await db.scalar(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.user_id == user_id)
    )
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found"
        )
    return purchase


async def _ensure_ready_for_spec(db: AsyncSession, purchase: Purchase) -> None:
    """Требует: анализ выполнен, и все вопросы (если они были заданы) отвечены.

    Логика:
    1. Анализ запускается автоматически, если его нет.
    2. Если анализ сказал needs_questions=false — ТЗ можно генерировать сразу.
    3. Если needs_questions=true, но вопросов ещё нет — 409, нужно вызвать /questions/generate.
    4. Если вопросы есть, но не все отвечены — 409 (включая «не знаю»).
    """
    analysis = await analysis_service.analyze_purchase(
        db, purchase.user_id, purchase.id
    )
    await db.refresh(purchase)

    if not analysis.needs_questions:
        # Вопросы не требуются — можно генерировать ТЗ
        return

    total = await db.scalar(
        select(func.count())
        .select_from(PurchaseQuestion)
        .where(PurchaseQuestion.purchase_id == purchase.id)
    )
    if not total:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Анализ показал, что для полного ТЗ не хватает данных. "
                "Сначала запросите вопросы: POST /purchases/{id}/questions/generate"
            ),
        )

    unanswered = await db.scalar(
        select(func.count())
        .select_from(PurchaseQuestion)
        .where(
            PurchaseQuestion.purchase_id == purchase.id,
            PurchaseQuestion.answered_at.is_(None),
        )
    )
    if unanswered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Есть {unanswered} неотвеченных вопросов. "
                "Ответьте на все (или отметьте dont_know=true) перед генерацией ТЗ."
            ),
        )


async def _build_prompt(db: AsyncSession, purchase: Purchase) -> str:
    """Описание + structured_fields + ответы на вопросы (FR-DLG-03)."""
    fields = purchase.structured_fields or {}
    lines = [
        f"Название закупки: {purchase.title}",
        f"Описание: {purchase.description}",
    ]
    labels = {
        "address": "Адрес объекта",
        "work_type": "Вид работ",
        "desired_dates": "Желаемые сроки",
        "constraints": "Ограничения",
        "contractor_requirements": "Требования к подрядчику",
        "budget": "Бюджет",
    }
    for key, label in labels.items():
        if fields.get(key):
            lines.append(f"{label}: {fields[key]}")

    questions = list(
        (
            await db.execute(
                select(PurchaseQuestion)
                .where(PurchaseQuestion.purchase_id == purchase.id)
                .order_by(PurchaseQuestion.round, PurchaseQuestion.order)
            )
        )
        .scalars()
        .all()
    )
    answered = [q for q in questions if q.answer_source == "user_defined"]
    dont_know = [q for q in questions if q.answer_source == "dont_know"]

    if answered:
        lines.append("\nУточнения от пользователя:")
        for q in answered:
            lines.append(f"- {q.text} → {q.answer}")

    if dont_know:
        lines.append(
            "\nПользователь не знает ответов на эти вопросы — подставь "
            "типовые значения и добавь в assumptions с source = "
            '"typical_assumption":'
        )
        for q in dont_know:
            lines.append(f"- {q.text}")

    return "\n".join(lines)


async def _save_new_version(
    db: AsyncSession,
    purchase_id: UUID,
    content: TechnicalSpecification,
    assumptions,
) -> Specification:
    """Создаёт новую версию ТЗ и переключает is_current. Не коммитит"""
    # Снимаем is_current у предыдущих версий — ровно одна актуальная
    await db.execute(
        update(Specification)
        .where(Specification.purchase_id == purchase_id)
        .values(is_current=False)
    )

    # Следующий номер версии: max(version)+1. Не полагаемся на счётчик в БД, чтобы номер был предсказуем и не зависел от sequence
    next_version = (
        await db.scalar(
            select(Specification.version)
            .where(Specification.purchase_id == purchase_id)
            .order_by(Specification.version.desc())
            .limit(1)
        )
        or 0
    ) + 1

    spec = Specification(
        purchase_id=purchase_id,
        version=next_version,
        # mode="json" — чтобы datetime/UUID/enum стали JSON-совместимыми для JSONB
        content=content.model_dump(mode="json"),
        is_current=True,
    )
    db.add(spec)
    # flush() — получаем spec.id для FK в assumptions, но коммитим всё одной транзакцией
    await db.flush()

    for a in assumptions:
        db.add(
            SpecAssumption(
                specification_id=spec.id,
                text=a.text,
                source=a.source.value if hasattr(a.source, "value") else a.source,
                requires_check=a.requires_check,
            )
        )
    return spec


def _section_wrapper(section: str):
    """Возвращает Pydantic-класс-обёртку для раздела, чтобы LLM вернула object

    Для объектных разделов (materials, quality, deadlines, ...) обёртка
    с полем value, для списковых (work_items, volumes, ...) — с полем items
    Ollama format требует object на верхнем уровне, поэтому обёртка нужна
    """
    from pydantic import BaseModel, Field

    from app.schemas import specifications as s

    object_map = {
        "general_info": s.GeneralInfo,
        "object_description": s.ObjectDescription,
        "materials": s.MaterialsRequirements,
        "quality": s.QualityRequirements,
        "deadlines": s.Deadlines,
        "conditions": s.Conditions,
        "contractor_requirements": s.ContractorRequirements,
        "acceptance": s.Acceptance,
        "warranty": s.Warranty,
    }
    list_map = {
        "work_items": s.WorkItem,
        "volumes": s.VolumeItem,
        "normative_references": s.NormativeReference,
    }

    if section in object_map:
        el = object_map[section]

        class _V(BaseModel):
            value: el  # type: ignore[valid-type]

        return _V

    el = list_map[section]

    class _L(BaseModel):
        items: list[el] = Field(default_factory=list)  # type: ignore[valid-type]

    return _L


def purchase_description(spec: TechnicalSpecification) -> str:
    """Короткое описание для промпта перегенерации: объект + дефект"""
    return (
        f"{spec.object_description.defect or ''} "
        f"на объекте {spec.general_info.object_name or 'не указан'}"
    ).strip()
