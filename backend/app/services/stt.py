"""Speech to text with faster-whisper. Optional: the app runs fine without it,
and the microphone button then explains what to install."""

import glob
import logging
import os
import re
import tempfile
import threading
from typing import Protocol

from ..config import settings
from .rag import list_topics

logger = logging.getLogger("uvicorn.error")

LANGUAGES = {"en", "ml"}
MALAYALAM = re.compile(r"[ഀ-ൿ]")
MAX_PROMPT_CHARS = 600  # Whisper only reads the last ~224 tokens of a prompt

# What "auto" picks. large-v3 makes far fewer mistakes (and is the only usable one for
# Malayalam) but is too slow on a laptop CPU, so the CPU gets small.
GPU_MODEL = "large-v3"
CPU_MODEL = "small"

TRANSCRIBE_OPTIONS = {
    "beam_size": 5,
    "best_of": 5,
    # Off: otherwise one misheard word is fed back in and the mistake repeats or snowballs.
    "condition_on_previous_text": False,
    "without_timestamps": True,
    "vad_filter": True,  # cut silence, the main source of made-up words
}


def _add_nvidia_dll_dirs() -> None:
    """The pip CUDA packages (nvidia-cublas-cu12, nvidia-cudnn-cu12) put their DLLs in
    site-packages/nvidia/*/bin, which Windows does not search on its own."""
    if os.name != "nt":
        return
    try:
        import nvidia
    except ImportError:
        return
    for root in nvidia.__path__:
        for bin_dir in glob.glob(os.path.join(root, "*", "bin")):
            os.add_dll_directory(bin_dir)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


def gpu_ready() -> bool:
    """True when an NVIDIA card and the CUDA libraries Whisper needs are both present.
    Checked up front because a missing CUDA library can crash the server mid-transcription."""
    try:
        import ctranslate2
    except ImportError:
        return False
    if ctranslate2.get_cuda_device_count() < 1:
        return False
    if os.name == "nt":
        import ctypes

        try:
            for dll in ("cublas64_12.dll", "cudnn_ops64_9.dll"):
                ctypes.WinDLL(dll)
        except OSError:
            return False
    return True


def resolve_runtime(model: str, device: str, compute_type: str) -> tuple[str, str, str]:
    """Fills in any "auto" setting: the GPU with large-v3 when it can, otherwise the CPU with small."""
    if device == "auto":
        device = "cuda" if gpu_ready() else "cpu"
    if compute_type == "auto":
        compute_type = "int8_float16" if device == "cuda" else "int8"
    if model == "auto":
        model = GPU_MODEL if device == "cuda" else CPU_MODEL
    return model, device, compute_type


def is_real_speech(segment) -> bool:
    """Whisper invents text for noise ("Thank you for watching."). Drop a piece it was
    both fairly sure was not speech and unsure of the words."""
    return not (getattr(segment, "no_speech_prob", 0.0) > 0.6 and getattr(segment, "avg_logprob", 0.0) < -1.0)


def vocabulary_prompt(language: str) -> str | None:
    """The course note titles in the spoken language, e.g. "Topics: Kirchhoff's laws, Ohm's law."
    Without them Whisper guesses at course terms in quiet or noisy recordings
    ("What is owns a lot?"); with them it spells them right. None when there are no notes."""
    topics = [t for t in list_topics() if bool(MALAYALAM.search(t)) == (language == "ml")]
    picked: list[str] = []
    length = 0
    for topic in topics:
        if length + len(topic) + 2 > MAX_PROMPT_CHARS:
            break
        picked.append(topic)
        length += len(topic) + 2
    if not picked:
        return None
    joined = ", ".join(picked)
    return f"Topics: {joined}." if language == "en" else f"{joined}."


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
            _add_nvidia_dll_dirs()
            model, device, compute_type = resolve_runtime(
                settings.whisper_model, settings.whisper_device, settings.whisper_compute_type
            )
            attempts = [(model, device, compute_type)]
            if device == "cuda" and settings.whisper_device == "auto":
                # If the card won't start, the CPU still works, just slower.
                attempts.append(resolve_runtime(settings.whisper_model, "cpu", "auto"))
            for model, device, compute_type in attempts:
                logger.info("Loading speech model %r on %s (first use downloads it)…", model, device)
                try:
                    self._model = WhisperModel(model, device=device, compute_type=compute_type)
                    return self._model
                except Exception as exc:
                    error = exc
                    logger.exception("Could not load the speech model on %s", device)
            raise SpeechUnavailable(
                "The speech model could not start. For the first run it needs internet to "
                "download. If you set WHISPER_DEVICE=cuda, try WHISPER_DEVICE=auto or cpu "
                "and WHISPER_COMPUTE_TYPE=auto in .env."
            ) from error

    def transcribe(self, audio: bytes, language: str) -> str:
        model = self._load()
        # faster-whisper reads from a file; keep it only as long as needed.
        fd, path = tempfile.mkstemp(suffix=".webm")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(audio)
            segments, _info = model.transcribe(
                path,
                language=language,
                initial_prompt=vocabulary_prompt(language),
                **TRANSCRIBE_OPTIONS,
            )
            return " ".join(s.text.strip() for s in segments if is_real_speech(s)).strip()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


_transcriber = WhisperTranscriber()


def get_transcriber() -> Transcriber:
    """FastAPI dependency. Tests override this."""
    return _transcriber
