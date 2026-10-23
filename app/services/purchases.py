from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase import Purchase
from app.schemas.purchases import PurchaseCreate
from app.services import analysis_service, question_service


async def create_purchase(
    db: AsyncSession, user_id: UUID, payload: PurchaseCreate
) -> Purchase:
    purchase = Purchase(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        structured_fields=payload.structured_fields.model_dump(exclude_none=True),
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)

    try:
        analysis = await analysis_service.analyze_purchase(db, user_id, purchase.id)
        await db.refresh(purchase)
    except HTTPException:
        # LLM недоступна - закупка создана, анализ можно повторить позже
        return purchase

    # Если анализ сказал "нужны вопросы" - генерируем их сразу
    if analysis.needs_questions:
        try:
            await question_service.generate_questions(db, user_id, purchase.id)
            await db.refresh(purchase)
        except HTTPException:
            # Не смогли сгенерировать - не ломаем создание
            pass

    return purchase


async def get_purchase(db: AsyncSession, user_id: UUID, purchase_id: UUID) -> Purchase:
    result = await db.execute(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.user_id == user_id)
    )
    purchase = result.scalar_one_or_none()
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found"
        )
    return purchase


async def list_purchases(db: AsyncSession, user_id: UUID) -> list[Purchase]:
    result = await db.execute(
        select(Purchase)
        .where(Purchase.user_id == user_id)
        .order_by(Purchase.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_purchase(db: AsyncSession, user_id: UUID, purchase_id: UUID) -> None:
    purchase = await get_purchase(db, user_id, purchase_id)
    await db.delete(purchase)
    await db.commit()
