from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, purchases, questions, specifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth.router)
app.include_router(purchases.router)
app.include_router(questions.router)
app.include_router(specifications.router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
