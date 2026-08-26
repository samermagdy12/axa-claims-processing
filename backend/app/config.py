from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "change-this-development-secret-before-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_ORIGINS: str = "http://localhost:8443,http://127.0.0.1:8443"
    UPLOAD_DIR: str = "uploads"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_VISION_MODEL: str | None = None
    GROQ_API_KEY: str | None = None
    GROQ_VISION_MODEL: str | None = None
    OCR_API_TIMEOUT_SECONDS: float = 45.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
