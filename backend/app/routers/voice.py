import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..config import settings
from ..models import User
from ..schemas import SpeakRequest
from ..security import get_current_user
from ..services.stt import LANGUAGES, SpeechUnavailable, Transcriber, get_transcriber
from ..services.tts import Speaker, VoiceUnavailable, get_speaker

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


@router.get("/options")
def voice_options(_user: User = Depends(get_current_user)):
    """Tells the web app who reads answers aloud: "elevenlabs" (POST /voice/speak) or "browser"."""
    return {"speech": settings.tts_provider}


@router.post("/speak")
def speak(
    body: SpeakRequest,
    _user: User = Depends(get_current_user),
    speaker: Speaker | None = Depends(get_speaker),
):
    """Reads text aloud with a realistic voice and returns MP3 audio."""
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "There is nothing to read aloud.")
    if len(text) > settings.max_speech_chars:
        raise HTTPException(413, f"That is too long to read in one go (limit {settings.max_speech_chars} characters).")
    if speaker is None:
        raise HTTPException(503, "Realistic voices are turned off, so this computer's voice reads answers instead.")

    try:
        audio = speaker.synthesize(text, body.language, body.previous_text.strip(), body.next_text.strip())
    except VoiceUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception:
        logger.exception("Text to speech failed")
        raise HTTPException(502, "Couldn't make the spoken answer. This computer's voice will read it instead.")
    return Response(audio, media_type="audio/mpeg", headers={"cache-control": "no-store"})
