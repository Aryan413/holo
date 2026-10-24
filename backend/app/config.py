import re

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-insecure-secret-change-before-deploying"

# Free local AI servers and where they listen by default.
LOCAL_BASE_URLS = {
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}
KNOWN_PROVIDERS = {"echo", "anthropic", "openai_compatible", *LOCAL_BASE_URLS}
TTS_PROVIDERS = {"browser", "elevenlabs"}


class Settings(BaseSettings):
    """All configuration comes from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "dev"  # set to "production" when deployed
    database_url: str = "sqlite:///./holox.db"

    jwt_secret: str = DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    # Teachers can only register with this code. Empty = teacher signup disabled.
    teacher_signup_code: str = ""

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Folder of course notes the tutor searches. Empty = the ai-engine/notes folder.
    notes_dir: str = ""

    # Folder with the web app (index.html). Empty = the repo's dashboard/ folder.
    web_dir: str = ""

    # Which AI writes the tutor's answers:
    #   echo, anthropic, ollama, lmstudio, openai_compatible  (see .env.example)
    llm_provider: str = "echo"
    llm_api_key: str = ""
    llm_model: str = ""  # required for local providers; anthropic defaults to claude-sonnet-5-5
    llm_base_url: str = ""  # only needed for openai_compatible
    llm_timeout_seconds: int = 120  # local models on a laptop CPU can be slow

    # Speech to text for the microphone button (needs `pip install -r requirements-voice.txt`).
    # Model sizes: tiny, base, small, medium, large-v3. Bigger = more accurate, slower,
    # and the only realistic choice for Malayalam. Downloaded once on first use.
    # "auto" everywhere = large-v3 on an NVIDIA card when the CUDA libraries are there
    # (requirements-voice-gpu.txt), otherwise small on the CPU.
    whisper_model: str = "auto"
    whisper_device: str = "auto"  # auto, cpu or cuda
    whisper_compute_type: str = "auto"  # auto, int8 (cpu), float16 or int8_float16 (cuda)
    max_audio_mb: int = 10

    # Voice for read-aloud answers:
    #   browser     the computer's own voices (free, works offline, sounds robotic)
    #   elevenlabs  realistic voices from ElevenLabs (needs ELEVENLABS_API_KEY, costs per character)
    tts_provider: str = "browser"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # "George", calm male narrator; any Voice Library ID works
    elevenlabs_model: str = "eleven_v4"  # eleven_v4 / eleven_v3 speak Malayalam, eleven_multilingual_v2 does not
    elevenlabs_timeout_seconds: int = 30
    max_speech_chars: int = 3000  # per request; the web app sends a few sentences at a time

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _reject_dev_secret_in_production(self):
        if self.environment == "production" and self.jwt_secret == DEV_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong random value in production")
        return self

    @model_validator(mode="after")
    def _check_llm_settings(self):
        provider = self.llm_provider
        if provider not in KNOWN_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of: {', '.join(sorted(KNOWN_PROVIDERS))}")
        if provider == "anthropic" and not self.llm_api_key:
            raise ValueError("LLM_PROVIDER=anthropic needs LLM_API_KEY")
        if (provider in LOCAL_BASE_URLS or provider == "openai_compatible") and not self.llm_model:
            raise ValueError(
                f"LLM_PROVIDER={provider} needs LLM_MODEL (for Ollama, the name shown by `ollama list`)"
            )
        if provider == "openai_compatible" and not self.llm_base_url:
            raise ValueError("LLM_PROVIDER=openai_compatible needs LLM_BASE_URL")
        return self

    @model_validator(mode="after")
    def _check_tts_settings(self):
        if self.tts_provider not in TTS_PROVIDERS:
            raise ValueError(f"TTS_PROVIDER must be one of: {', '.join(sorted(TTS_PROVIDERS))}")
        if self.tts_provider == "elevenlabs" and not self.elevenlabs_api_key:
            raise ValueError("TTS_PROVIDER=elevenlabs needs ELEVENLABS_API_KEY")
        # The ID goes into the request URL, so only allow the letters and digits ElevenLabs uses.
        if not re.fullmatch(r"[A-Za-z0-9]{1,64}", self.elevenlabs_voice_id):
            raise ValueError("ELEVENLABS_VOICE_ID must be the voice's ID (letters and digits), not its name")
        return self


settings = Settings()
