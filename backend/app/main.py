import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, dashboard, quiz, tutor


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for development. Switch to Alembic migrations before the schema starts changing.
    Base.metadata.create_all(bind=engine)
    if settings.llm_provider == "echo":
        logger.warning(
            "LLM_PROVIDER=echo: tutor replies are placeholders. "
            "Set LLM_PROVIDER in .env (ollama, lmstudio or anthropic) for real answers."
        )
    yield


app = FastAPI(title="HoloX Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tutor.router)
app.include_router(quiz.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
