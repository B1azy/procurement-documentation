"""Уточняющий диалог"""

from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.questions import (
    BatchAnswerIn,
    QuestionAnswerIn,
    QuestionRead,
)
from app.services import question_service

router = APIRouter(prefix="/purchases/{purchase_id}/questions", tags=["questions"])


@router.post(
    "/generate",
    response_model=list[QuestionRead],
    status_code=status.HTTP_201_CREATED,
)
async def generate_questions(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> list[QuestionRead]:
    """Новый раунд вопросов (≤7). Раунд 1 — типовые+LLM, далее — только LLM"""
    questions = await question_service.generate_questions(
        db, current_user.id, purchase_id
    )
    return [QuestionRead.model_validate(q) for q in questions]


@router.get("/", response_model=list[QuestionRead])
async def list_questions(
    purchase_id: UUID, db: DbSession, current_user: CurrentUser
) -> list[QuestionRead]:
    """Все вопросы по закупке (все раунды)"""
    questions = await question_service.list_questions(db, current_user.id, purchase_id)
    return [QuestionRead.model_validate(q) for q in questions]


@router.post("/answer-batch", response_model=list[QuestionRead])
async def answer_batch(
    purchase_id: UUID,
    payload: BatchAnswerIn,
    db: DbSession,
    current_user: CurrentUser,
) -> list[QuestionRead]:
    """Batch-ответ на несколько вопросов. Атомарно: либо все, либо ни одного"""
    questions = await question_service.answer_questions_batch(
        db, current_user.id, purchase_id, payload
    )
    return [QuestionRead.model_validate(q) for q in questions]


@router.post("/{question_id}/answer", response_model=QuestionRead)
async def answer_one(
    purchase_id: UUID,
    question_id: UUID,
    payload: QuestionAnswerIn,
    db: DbSession,
    current_user: CurrentUser,
) -> QuestionRead:
    """Ответ на один вопрос. dont_know=true — типовое значение подставит LLM"""
    question = await question_service.answer_question(
        db, current_user.id, purchase_id, question_id, payload
    )
    return QuestionRead.model_validate(question)
