"""Text to speech for read-aloud answers. Optional: with TTS_PROVIDER=browser (the default)
the web app uses the computer's own voices and never calls this."""

import logging
from typing import Protocol

import httpx

from ..config import settings

logger = logging.getLogger("uvicorn.error")


class VoiceUnavailable(Exception):
    """The spoken answer could not be made. The message is safe to show to students."""


class Speaker(Protocol):
    def synthesize(self, text: str, language: str, previous_text: str = "", next_text: str = "") -> bytes:
        """Returns MP3 audio of the text read in the given language ("en" or "ml").
        previous_text / next_text are context only (not spoken), for smooth joins between pieces."""
        ...


class ElevenLabsSpeaker:
    """Calls the ElevenLabs text to speech API over HTTPS. The key never leaves the server."""

    URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def __init__(self, api_key: str, voice_id: str, model: str, timeout: float = 30):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.timeout = timeout

    def synthesize(self, text: str, language: str, previous_text: str = "", next_text: str = "") -> bytes:
        body = {"text": text, "model_id": self.model}
        # Pins the language (and how numbers are read). multilingual_v2 models reject this field.
        if not self.model.startswith("eleven_multilingual"):
            body["language_code"] = language
        if previous_text:
            body["previous_text"] = previous_text
        if next_text:
            body["next_text"] = next_text
        try:
            response = httpx.post(
                self.URL.format(voice_id=self.voice_id),
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": self.api_key, "content-type": "application/json", "accept": "audio/mpeg"},
                json=body,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("Could not reach ElevenLabs: %s", exc)
            raise VoiceUnavailable("Couldn't reach the voice service. Check the internet connection.") from exc

        status = response.status_code
        if status in (401, 403):
            logger.error("ElevenLabs refused the request (%s): check ELEVENLABS_API_KEY. %s", status, response.text[:300])
            raise VoiceUnavailable("The voice service isn't set up correctly. Ask a teacher to check the voice key.")
        if status == 429:
            logger.warning("ElevenLabs rate or quota limit: %s", response.text[:300])
            raise VoiceUnavailable("The voice service is busy or this month's voice allowance is used up.")
        if status >= 400:
            logger.error("ElevenLabs error %s: %s", status, response.text[:300])
            raise VoiceUnavailable("The voice service couldn't read this answer.")
        if not response.content:
            raise VoiceUnavailable("The voice service sent back no audio.")
        return response.content


def get_speaker() -> Speaker | None:
    """FastAPI dependency. None means the browser reads answers itself. Tests override this."""
    if settings.tts_provider == "elevenlabs":
        return ElevenLabsSpeaker(
            settings.elevenlabs_api_key,
            settings.elevenlabs_voice_id,
            settings.elevenlabs_model,
            settings.elevenlabs_timeout_seconds,
        )
    return None
