import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine
from .migrations import DatabaseOutOfStep, prepare_database
from .routers import auth, dashboard, quiz, tutor, voice


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables come from Alembic migrations (backend/migrations). The shared database is only
    # checked here, never changed: see app/migrations.py.
    try:
        logger.info("Database: %s", prepare_database(engine, settings.database_url))
    except DatabaseOutOfStep as problem:
        logger.error("The server can't start: %s", problem)
        raise SystemExit(1) from None
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
app.include_router(voice.router)
app.include_router(quiz.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# The web app (dashboard/ folder) is served from the same address as the API, so
# http://127.0.0.1:8000/ opens it. Mounted last so every API route above wins.
WEB_DIR = Path(settings.web_dir) if settings.web_dir else Path(__file__).resolve().parents[2] / "dashboard"
if (WEB_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
