from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-insecure-secret-change-before-deploying"


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

    # "echo" (offline, for development) or "anthropic"
    llm_provider: str = "echo"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _reject_dev_secret_in_production(self):
        if self.environment == "production" and self.jwt_secret == DEV_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong random value in production")
        return self


settings = Settings()
