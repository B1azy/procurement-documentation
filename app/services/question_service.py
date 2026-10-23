"""Генерация уточняющих вопросов и приём ответов"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.purchase import Purchase, PurchaseStatus
from app.models.question import PurchaseQuestion, QuestionAnswerSource
from app.schemas.questions import (
    BatchAnswerIn,
    QuestionAnswerIn,
    QuestionSet,
)
from app.services import analysis_service
from app.services import typical_questions as typical
from app.services.llm.factory import get_llm_client

MAX_QUESTIONS_PER_ROUND = 7
MAX_ROUNDS = 3

QUESTIONS_SYSTEM_PROMPT = """Ты — помощник по подготовке технического задания на подрядные работы и услуги.

Найди в описании закупки пробелы, без которых нельзя составить полное ТЗ, и задай уточняющие вопросы.

ПРАВИЛА:
1. Не более 7 вопросов за раз.
2. Простой язык, без профессионального жаргона.
3. К каждому вопросу ОБЯЗАТЕЛЬНО добавь hint — короткую подсказку или пример. Пустой hint допустим только для тривиальных вопросов с однозначным ответом.
4. К вопросам с ограниченным набором ответов добавь 2–4 варианта в options.
5. НЕ задавай вопросы про финансирование, юридические согласования, разрешения, владельцев зданий — это не входит в техническое задание.
6. Спрашивай только то, что попадёт в разделы ТЗ: описание объекта, перечень работ, объёмы, материалы, качество, сроки, условия доступа, требования к подрядчику, критерии приёмки, гарантия.
7. Не спрашивай то, что уже есть в описании или полях.
8. Не повторяй вопросы из списка «уже будут заданы».
9. Если пробелов нет — верни пустой список questions.
10. Отвечай на русском. Верни ТОЛЬКО JSON по схеме.
"""


async def generate_questions(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> list[PurchaseQuestion]:
    """Генерирует раунд вопросов.

    Логика:
    1. Автоматически запускает анализ закупки, если его ещё нет.
    2. Если анализ сказал needs_questions=false — возвращает [] и переводит
       закупку в READY_FOR_SPEC. Вопросы не нужны.
    3. Иначе — генерирует раунд (типовые + LLM).
    """
    purchase = await _get_owned_purchase(db, user_id, purchase_id)

    # Если уже есть вопросы - перепроверяем с учётом ответов.
    # Если вопросов нет (первый вызов) - обычный анализ (кэш, если есть).
    has_questions = (
        await db.scalar(
            select(func.count())
            .select_from(PurchaseQuestion)
            .where(PurchaseQuestion.purchase_id == purchase_id)
        )
    ) or 0

    analysis = await analysis_service.analyze_purchase(
        db, user_id, purchase_id, force=has_questions > 0
    )
    await db.refresh(purchase)

    if not analysis.needs_questions:
        # Ответы закрыли пробелы - больше вопросов не нужно
        if purchase.status != PurchaseStatus.READY_FOR_SPEC.value:
            purchase.status = PurchaseStatus.READY_FOR_SPEC.value
            await db.commit()
        return []

    # Авто-анализ при первом обращении. Повторные вызовы используют кэш.
    analysis = await analysis_service.analyze_purchase(db, user_id, purchase_id)
    await db.refresh(purchase)

    if not analysis.needs_questions:
        # Вопросов не требуется. Переводим закупку в готовность к ТЗ.
        if purchase.status != PurchaseStatus.READY_FOR_SPEC.value:
            purchase.status = PurchaseStatus.READY_FOR_SPEC.value
            await db.commit()
        return []

    # Дальше — обычная логика генерации раунда
    last_round = (
        await db.scalar(
            select(func.max(PurchaseQuestion.round)).where(
                PurchaseQuestion.purchase_id == purchase_id
            )
        )
        or 0
    )

    if last_round >= MAX_ROUNDS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Достигнут лимит раундов ({MAX_ROUNDS}). "
                "Сгенерируйте ТЗ с текущими ответами."
            ),
        )

    if last_round > 0:
        unanswered = await db.scalar(
            select(func.count())
            .select_from(PurchaseQuestion)
            .where(
                PurchaseQuestion.purchase_id == purchase_id,
                PurchaseQuestion.round == last_round,
                PurchaseQuestion.answered_at.is_(None),
            )
        )
        if unanswered:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Есть {unanswered} неотвеченных вопросов в раунде "
                    f"{last_round}. Ответьте на все перед новым раундом."
                ),
            )

    next_round = last_round + 1

    # Типовые только в первом раунде. Вид работ берём из анализа — он точнее,
    # чем эвристика по описанию.
    typical_items: list[dict] = []
    if next_round == 1:
        fields = purchase.structured_fields or {}
        work_type_for_typical = analysis.work_type
        if work_type_for_typical.lower() in {
            "work",
            "service",
            "goods",
            "работа",
            "услуга",
            "товар",
        }:
            work_type_for_typical = None
        candidates = typical.get_questions_for_work_type(analysis.work_type)

        if fields.get("address"):
            candidates = [q for q in candidates if "адрес" not in q["text"].lower()]
        if fields.get("desired_dates"):
            candidates = [q for q in candidates if "срок" not in q["text"].lower()]

        typical_items = candidates[:MAX_QUESTIONS_PER_ROUND]

    remaining = MAX_QUESTIONS_PER_ROUND - len(typical_items)
    llm_items: list[dict] = []
    if remaining > 0:
        # Загружаем ответы предыдущих раундов - модель не должна их переспрашивать
        prev = await db.execute(
            select(PurchaseQuestion)
            .where(
                PurchaseQuestion.purchase_id == purchase_id,
                PurchaseQuestion.answered_at.is_not(None),
            )
            .order_by(PurchaseQuestion.round, PurchaseQuestion.order)
        )
        prev_answers: list[tuple[str, str]] = []
        for q in prev.scalars().all():
            if q.answer_source == "user_defined" and q.answer is not None:
                prev_answers.append((q.text, q.answer))
            else:
                # dont_know или пустой ответ - для модели это "не знает"
                prev_answers.append((q.text, "не знает"))

        prompt = _build_questions_prompt(
            purchase,
            next_round,
            existing_texts=[q["text"] for q in typical_items],
            missing_info=analysis.missing_info,
            prev_answers=prev_answers,
        )
        client = get_llm_client()
        try:
            result = await client.generate_structured(
                model=settings.llm_model_questions or settings.llm_model,
                prompt=prompt,
                response_model=QuestionSet,
                system_prompt=QUESTIONS_SYSTEM_PROMPT,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Модель вернула невалидный ответ: {exc}",
            ) from exc
        llm_items = [q.model_dump() for q in result.questions][:remaining]

    created: list[PurchaseQuestion] = []
    for idx, item in enumerate(typical_items + llm_items, start=1):
        question = PurchaseQuestion(
            purchase_id=purchase_id,
            round=next_round,
            order=idx,
            text=item["text"],
            hint=item.get("hint"),
            options=item.get("options") or [],
        )
        db.add(question)
        created.append(question)

    if created:
        purchase.status = PurchaseStatus.QUESTIONS_PENDING.value

    await db.commit()
    for q in created:
        await db.refresh(q)
    return created


def _build_questions_prompt(
    purchase: Purchase,
    next_round: int,
    existing_texts: list[str],
    missing_info: list[str],
    prev_answers: list[tuple[str, str]] | None = None,
) -> str:
    # Промт для LLM с подсказкой из анализа и уже полученными ответами
    fields = purchase.structured_fields or {}
    lines = [
        f"Название закупки: {purchase.title}",
        f"Описание: {purchase.description}",
    ]
    if fields:
        lines.append(f"Структурированные поля: {fields}")

    if missing_info:
        lines.append(
            "\nАнализ уже выявил, что не хватает следующих сведений - "
            "задай вопросы именно про них:"
        )
        for m in missing_info:
            lines.append(f"- {m}")

    if prev_answers:
        lines.append("\nПользователь УЖЕ ответил на эти вопросы - НЕ ПЕРЕСПРАШИВАЙ:")
        for question, answer in prev_answers:
            lines.append(f"- {question} → {answer}")

    if existing_texts:
        lines.append("\nСледующие вопросы УЖЕ будут заданы - НЕ ПОВТОРЯЙ их:")
        for t in existing_texts:
            lines.append(f"- {t}")

    lines.append(
        f"\nРаунд {next_round} из {MAX_ROUNDS}. "
        "Не более 7 вопросов, к каждому обязательно hint"
    )
    return "\n".join(lines)


async def answer_question(
    db: AsyncSession,
    user_id: UUID,
    purchase_id: UUID,
    question_id: UUID,
    payload: QuestionAnswerIn,
) -> PurchaseQuestion:
    """Ответ на один вопрос. Кидает 409, если вопрос уже отвечен

    Логика «не знаю»: answer=None, answer_source="dont_know"
    Типовое значение подставит LLM при генерации ТЗ и пометит в assumptions
    """
    await _get_owned_purchase(db, user_id, purchase_id)

    question = await db.scalar(
        select(PurchaseQuestion).where(
            PurchaseQuestion.id == question_id,
            PurchaseQuestion.purchase_id == purchase_id,
        )
    )
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if question.answered_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Question already answered"
        )

    _apply_answer(question, payload)
    await db.commit()
    await db.refresh(question)
    return question


async def answer_questions_batch(
    db: AsyncSession,
    user_id: UUID,
    purchase_id: UUID,
    payload: BatchAnswerIn,
) -> list[PurchaseQuestion]:
    """Batch-ответ. Атомарность: если хоть один вопрос чужой/отвечен/не найден —
    весь batch отклоняется, БД не меняется.

    Порядок:
    1. Владелец закупки (404)
    2. Все вопросы найдены и принадлежат закупке (404, если хоть один чужой)
    3. Ни один ещё не отвечен (409, если хоть один закрыт)
    4. Валидация каждого ответа (422, если пустой и не dont_know)
    5. Применяем всё одной транзакцией
    """
    await _get_owned_purchase(db, user_id, purchase_id)

    q_ids = [a.question_id for a in payload.answers]
    # Дубликаты id в одном batch — ошибка ввода: непонятно, какой ответ главный
    if len(q_ids) != len(set(q_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch содержит дублирующиеся question_id",
        )

    result = await db.execute(
        select(PurchaseQuestion).where(
            PurchaseQuestion.id.in_(q_ids),
            PurchaseQuestion.purchase_id == purchase_id,
        )
    )
    by_id = {q.id: q for q in result.scalars().all()}

    missing = set(q_ids) - set(by_id.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Вопросы не найдены: {sorted(map(str, missing))}",
        )

    already = [str(q.id) for q in by_id.values() if q.answered_at is not None]
    if already:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Уже отвечены: {already}",
        )

    # Валидируем все ответы до записи — чтобы не оставить частично применённый batch
    for a in payload.answers:
        _validate_answer(a)

    for a in payload.answers:
        _apply_answer(by_id[a.question_id], a)

    await db.commit()
    for q in by_id.values():
        await db.refresh(q)

    # Возвращаем в порядке входного batch — предсказуемо для клиента
    return [by_id[a.question_id] for a in payload.answers]


async def list_questions(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> list[PurchaseQuestion]:
    """Все вопросы по закупке, сгруппированные по раундам и порядку"""
    await _get_owned_purchase(db, user_id, purchase_id)
    result = await db.execute(
        select(PurchaseQuestion)
        .where(PurchaseQuestion.purchase_id == purchase_id)
        .order_by(PurchaseQuestion.round, PurchaseQuestion.order)
    )
    return list(result.scalars().all())


# --- Внутренние помощники ---


def _validate_answer(payload: QuestionAnswerIn) -> None:
    """Пустой answer без dont_know — ошибка ввода"""
    if not payload.dont_know and not (payload.answer and payload.answer.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Нужно указать answer или dont_know=true",
        )


def _apply_answer(question: PurchaseQuestion, payload: QuestionAnswerIn) -> None:
    # Применяет один ответ к ORM-объекту, не коммитит - это делает вызывающий
    if payload.dont_know:
        question.answer = None
        question.answer_source = QuestionAnswerSource.DONT_KNOW
    else:
        # Валидация гарантирует непустой answer (см _validate_answer)
        # Явная проверка нужна, чтобы Pylance видел не-None
        if payload.answer is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Нужно указать answer или dont_know=true",
            )
        question.answer = payload.answer.strip()
        question.answer_source = QuestionAnswerSource.USER
    # func.now() - серверное время, не зависит от часов приложения
    question.answered_at = func.now()


async def _get_owned_purchase(
    db: AsyncSession, user_id: UUID, purchase_id: UUID
) -> Purchase:
    """Проверка владельца. 404"""
    purchase = await db.scalar(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.user_id == user_id)
    )
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found"
        )
    return purchase
