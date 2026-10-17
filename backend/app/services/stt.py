"""Speech to text with faster-whisper. Optional: the app runs fine without it,
and the microphone button then explains what to install."""

import logging
import os
import tempfile
import threading
from typing import Protocol

from ..config import settings

logger = logging.getLogger("uvicorn.error")

LANGUAGES = {"en", "ml"}


class SpeechUnavailable(Exception):
    """Speech to text can't run here. The message says what to do about it."""


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, language: str) -> str: ...


class WhisperTranscriber:
    """Loads the model on first use (it is big) and keeps it in memory."""

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise SpeechUnavailable(
                    "Voice input isn't installed. In the backend folder run: "
                    "pip install -r requirements-voice.txt, then restart the server."
                ) from exc
            logger.info("Loading speech model %r (first use downloads it)…", settings.whisper_model)
            try:
                self._model = WhisperModel(
                    settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
            except Exception as exc:
                logger.exception("Could not load the speech model")
                raise SpeechUnavailable(
                    "The speech model could not start. For the first run it needs internet to "
                    "download. If you set WHISPER_DEVICE=cuda, try WHISPER_DEVICE=cpu and "
                    "WHISPER_COMPUTE_TYPE=int8 in .env."
                ) from exc
            return self._model

    def transcribe(self, audio: bytes, language: str) -> str:
        model = self._load()
        # faster-whisper reads from a file; keep it only as long as needed.
        fd, path = tempfile.mkstemp(suffix=".webm")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(audio)
            segments, _info = model.transcribe(
                path, language=language, vad_filter=True, beam_size=5
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


_transcriber = WhisperTranscriber()


def get_transcriber() -> Transcriber:
    """FastAPI dependency. Tests override this."""
    return _transcriber
