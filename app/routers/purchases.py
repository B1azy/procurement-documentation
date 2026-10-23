from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.analysis import AnalysisRead
from app.schemas.purchases import PurchaseCreate, PurchaseRead
from app.services import analysis_service
from app.services import purchases as purchases_service

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("/", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate, db: DbSession, current_user: CurrentUser
) -> PurchaseRead:
    purchase = await purchases_service.create_purchase(db, current_user.id, payload)
    return PurchaseRead.model_validate(purchase)


@router.get("/", response_model=list[PurchaseRead])
async def list_purchases(
    db: DbSession, current_user: CurrentUser
) -> list[PurchaseRead]:
    purchases = await purchases_service.list_purchases(db, current_user.id)
    return [PurchaseRead.model_validate(p) for p in purchases]


@router.get("/{purchase_id}", response_model=PurchaseRead)
async def get_purchase(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> PurchaseRead:
    purchase = await purchases_service.get_purchase(db, current_user.id, purchase_id)
    return PurchaseRead.model_validate(purchase)


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> None:
    await purchases_service.delete_purchase(db, current_user.id, purchase_id)


@router.post("/{purchase_id}/analyze", response_model=AnalysisRead)
async def analyze(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> AnalysisRead:
    """Анализ закупки: тип предмета, вид, полнота, нужны ли вопросы.

    Вызывается автоматически из /questions/generate и /specifications/generate,
    если анализ ещё не выполнен. Явный вызов — для повторного запуска
    после правки описания или для отладки.
    """
    result = await analysis_service.analyze_purchase(db, current_user.id, purchase_id)
    return AnalysisRead(
        purchase_type=result.purchase_type,
        analysis=result,
    )
