"""Эндпоинты модуля А: генерация, версии, ручная правка, перегенерация, экспорт"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.schemas.questions import SectionRegenerateIn
from app.schemas.specifications import (
    SpecificationListItem,
    SpecificationRead,
    TechnicalSpecification,
)
from app.services import docx_export, spec_generator

router = APIRouter(
    prefix="/purchases/{purchase_id}/specifications", tags=["specifications"]
)


@router.post(
    "/generate",
    response_model=SpecificationRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_draft(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> SpecificationRead:
    """Генерация ТЗ. Требует, чтобы все раунды вопросов были закрыты"""
    spec = await spec_generator.generate_draft(db, current_user.id, purchase_id)
    return SpecificationRead.model_validate(spec)


@router.get("/", response_model=list[SpecificationListItem])
async def list_versions(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> list[SpecificationListItem]:
    """История версий без content — только метаданные"""
    specs = await spec_generator.list_specifications(db, current_user.id, purchase_id)
    return [SpecificationListItem.model_validate(s) for s in specs]


# /current объявлен раньше /{spec_id}, иначе "current" уйдёт в UUID-парсер
@router.get("/current", response_model=SpecificationRead)
async def get_current(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> SpecificationRead:
    """Актуальная версия с полным content."""
    spec = await spec_generator.get_current_specification(
        db, current_user.id, purchase_id
    )
    return SpecificationRead.model_validate(spec)


@router.get("/{spec_id}", response_model=SpecificationRead)
async def get_version(
    purchase_id: UUID,
    spec_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> SpecificationRead:
    """Конкретная версия с полным content"""
    spec = await spec_generator.get_specification(
        db, current_user.id, purchase_id, spec_id
    )
    await db.refresh(spec, attribute_names=["assumptions"])
    return SpecificationRead.model_validate(spec)


@router.patch("/{spec_id}", response_model=SpecificationRead)
async def update_content(
    purchase_id: UUID,
    spec_id: UUID,
    payload: TechnicalSpecification,
    db: DbSession,
    current_user: CurrentUser,
) -> SpecificationRead:
    """Ручная правка всего ТЗ. Создаёт новую версию"""
    spec = await spec_generator.update_content(
        db, current_user.id, purchase_id, spec_id, payload
    )
    return SpecificationRead.model_validate(spec)


@router.post("/{spec_id}/regenerate-section", response_model=SpecificationRead)
async def regenerate_section(
    purchase_id: UUID,
    spec_id: UUID,
    payload: SectionRegenerateIn,
    db: DbSession,
    current_user: CurrentUser,
) -> SpecificationRead:
    """Перегенерация одного раздела с инструкцией. Создаёт новую версию"""
    spec = await spec_generator.regenerate_section(
        db,
        current_user.id,
        purchase_id,
        spec_id,
        payload.section,
        payload.instruction,
    )
    return SpecificationRead.model_validate(spec)


@router.get(
    "/{spec_id}/download",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            },
            "description": "DOCX-файл с ТЗ",
        }
    },
)
async def download_specification(
    purchase_id: UUID,
    spec_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Отдаёт DOCX указанной версии"""
    spec = await spec_generator.get_specification(
        db, current_user.id, purchase_id, spec_id
    )
    content = TechnicalSpecification.model_validate(spec.content)

    try:
        buffer = docx_export.render_specification(content, spec.version)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    filename = f"specification_v{spec.version}.docx"
    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
