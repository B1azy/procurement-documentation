"""Анализ закупки: тип предмета, вид, полнота, необходимость вопросов.

Вызывается автоматически из create_purchase, generate_questions и generate_draft,
если анализ ещё не выполнен или если нужно пересчитать с учётом ответов
на уточняющие вопросы. Также доступен явным эндпоинтом /analyze.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.purchase import Purchase, PurchaseStatus
from app.models.question import PurchaseQuestion
from app.schemas.analysis import PurchaseAnalysis
from app.services.llm.factory import get_llm_client

ANALYSIS_SYSTEM_PROMPT = """Ты — эксперт по закупкам подрядных работ и услуг.

Проанализируй описание закупки и уже полученные ответы пользователя
(если они есть) и определи ЧЕТЫРЕ вещи.

1. purchase_type — ТИП предмета закупки, строго одно из трёх:
   - "work" — работа: ремонт, замена, монтаж, установка, демонтаж, строительство, реконструкция
   - "service" — услуга: уборка, охрана, обслуживание, консультация, обучение
   - "goods" — товар: поставка материалов, оборудования, мебели
   Примеры: замена окон = work, ремонт кровли = work, уборка помещений = service,
   поставка плитки = goods.

2. work_type — КОНКРЕТНЫЙ ВИД работ/услуги/товара, короткой фразой на русском.
   Это НЕ тип из пункта 1. Примеры: "замена окна", "ремонт кровли", "укладка плитки",
   "установка доводчика", "устранение протечки", "уборка офиса", "поставка керамогранита".
   НИКОГДА не пиши сюда "work", "service", "goods" или их русские переводы.

3. completeness — полнота описания С УЧЁТОМ ответов:
   - "low" — только общее описание без цифр
   - "medium" — есть суть, но нет объёмов или сроков
   - "high" — есть объект, суть, объёмы, сроки

4. needs_questions и missing_info — нужны ли ЕЩЁ вопросы.
   - needs_questions = true только если после учёта уже полученных ответов
     для полного ТЗ всё ещё не хватает критичных данных.
   - missing_info — конкретный список пробелов. Пусто, если needs_questions = false.

ПРАВИЛА:
- Ответ "не знаю" от пользователя — НЕ пробел. Типовое значение подставит
  генератор ТЗ и пометит как допущение. Не включай такие темы в missing_info.
- Не спрашивай и не отмечай как пробел: финансирование, юридические согласования,
  разрешения, владельцев зданий — это вне рамок технического задания.
- Если ответы закрыли все ранее выявленные пробелы — needs_questions = false,
  missing_info = [].
- reasoning — одно-два предложения, для отладки.
- Отвечай на русском. Верни ТОЛЬКО JSON по схеме, без пояснений.
"""


async def analyze_purchase(
    db: AsyncSession,
    user_id: UUID,
    purchase_id: UUID,
    *,
    force: bool = False,
) -> PurchaseAnalysis:
    """Запускает анализ и сохраняет результат в закупку.

    force=False (по умолчанию): если анализ уже есть — возвращает кэш без LLM.
    force=True: пересчитывает, даже если анализ есть. Нужно после получения
    ответов на вопросы — старый анализ их не видел.

    Результат сохраняется в purchase.analysis (JSON) и purchase.purchase_type
    (отдельная колонка для фильтрации и отображения). Определённый вид работ
    подставляется в structured_fields.work_type, если пользователь его не указал.
    """
    purchase = await _get_owned_purchase(db, user_id, purchase_id)

    # Кэш: анализ не зависит от действий пользователя, пока описание не менялось
    # и пока не пришли новые ответы (тогда нужен force=True)
    if purchase.analysis is not None and not force:
        return PurchaseAnalysis.model_validate(purchase.analysis)

    prompt = await _build_analysis_prompt(db, purchase)
    client = get_llm_client()

    try:
        result = await client.generate_structured(
            model=settings.llm_model_questions or settings.llm_model,
            prompt=prompt,
            response_model=PurchaseAnalysis,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Модель вернула невалидный ответ при анализе: {exc}",
        ) from exc

    # Сохраняем результат
    purchase.analysis = result.model_dump(mode="json")
    purchase.purchase_type = result.purchase_type

    TYPE_VALUES = {"work", "service", "goods", "работа", "услуга", "товар"}
    fields = dict(purchase.structured_fields or {})
    if not fields.get("work_type") and result.work_type.lower() not in TYPE_VALUES:
        fields["work_type"] = result.work_type
        purchase.structured_fields = fields

    # Подставляем определённый вид работ, если пользователь его не указал
    fields = dict(purchase.structured_fields or {})
    if not fields.get("work_type"):
        fields["work_type"] = result.work_type
        purchase.structured_fields = fields

    # Если вопросы не нужны и закупка ещё в черновике — переводим в готовность
    if not result.needs_questions and purchase.status == PurchaseStatus.DRAFT.value:
        purchase.status = PurchaseStatus.READY_FOR_SPEC.value

    await db.commit()
    await db.refresh(purchase)
    return result


async def _build_analysis_prompt(db: AsyncSession, purchase: Purchase) -> str:
    """Собирает текст для модели: описание, поля и ответы на вопросы.

    Ответы на вопросы — критичны при force=True: без них анализ не увидит,
    что пробелы уже закрыты, и будет бесконечно находить новые.
    """
    fields = purchase.structured_fields or {}
    lines = [
        f"Название закупки: {purchase.title}",
        f"Описание: {purchase.description}",
    ]
    labels = {
        "address": "Адрес объекта",
        "work_type": "Вид работ (со слов пользователя)",
        "desired_dates": "Желаемые сроки",
        "constraints": "Ограничения",
        "contractor_requirements": "Требования к подрядчику",
        "budget": "Бюджет",
    }
    for key, label in labels.items():
        if fields.get(key):
            lines.append(f"{label}: {fields[key]}")

    # Подтягиваем ответы на вопросы. Без этого force-анализ бесполезен
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
        lines.append("\nПользователь уже ответил на вопросы:")
        for q in answered:
            lines.append(f"- {q.text} → {q.answer}")

    if dont_know:
        # Явно помечаем "не знаю" как НЕ пробел: типовое значение подставит
        # генератор ТЗ, это не повод задавать вопрос повторно
        lines.append(
            "\nПользователь ответил 'не знаю' на следующие вопросы. "
            "Это НЕ пробел — типовые значения подставит генератор ТЗ, "
            "не включай эти темы в missing_info:"
        )
        for q in dont_know:
            lines.append(f"- {q.text}")

    return "\n".join(lines)


async def _get_owned_purchase(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> Purchase:
    """Проверка владельца. 404, а не 403 — не подтверждаем существование чужой."""
    purchase = await db.scalar(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.user_id == user_id)
    )
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found"
        )
    return purchase
