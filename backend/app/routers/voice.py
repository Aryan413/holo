import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..config import settings
from ..models import User
from ..security import get_current_user
from ..services.stt import LANGUAGES, SpeechUnavailable, Transcriber, get_transcriber

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    _user: User = Depends(get_current_user),
    transcriber: Transcriber = Depends(get_transcriber),
):
    """Turns a short recording into text. The browser then puts it in the question box."""
    if language not in LANGUAGES:
        raise HTTPException(422, "language must be 'en' or 'ml'")

    limit = settings.max_audio_mb * 1024 * 1024
    data = audio.file.read(limit + 1)
    if not data:
        raise HTTPException(422, "The recording was empty. Try again and speak after pressing Speak.")
    if len(data) > limit:
        raise HTTPException(413, f"The recording is too long (limit {settings.max_audio_mb} MB). Try a shorter question.")

    try:
        text = transcriber.transcribe(data, language)
    except SpeechUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception:
        logger.exception("Speech to text failed")
        raise HTTPException(502, "Could not understand that recording. Try again, or type the question.")
    if not text:
        raise HTTPException(422, "I couldn't hear any speech. Check your microphone and try again.")
    return {"text": text}
