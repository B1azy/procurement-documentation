from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token
from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import Token
from app.schemas.users import UserCreate, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbSession) -> UserRead:
    user = await auth_service.register_user(db, payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    user = await auth_service.authenticate_user(db, form.username, form.password)
    return Token(access_token=create_access_token(subject=user.email))


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
