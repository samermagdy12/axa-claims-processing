from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "change-this-development-secret-before-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_ORIGINS: str = "http://localhost:8443,http://127.0.0.1:8443,http://192.168.1.19:8443"
    UPLOAD_DIR: str = "uploads"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_VISION_MODEL: str | None = None
    GROQ_API_KEY: str | None = None
    GROQ_VISION_MODEL: str | None = None
    OCR_API_TIMEOUT_SECONDS: float = 45.0
    # Claim analysis intentionally has independent models from Vision/OCR.
    OPENROUTER_LLM_MODEL: str | None = None
    GROQ_LLM_MODEL: str | None = None
    CLAIM_ANALYSIS_TIMEOUT_SECONDS: float = 60.0
    # Embeddings are also independent from both OCR and reasoning models.
    OPENROUTER_EMBEDDING_MODEL: str | None = None
    OPENROUTER_EMBEDDING_URL: str = "https://openrouter.ai/api/v1/embeddings"
    HANDBOOK_SOURCE_PATH: str = str(PROJECT_ROOT / "data" / "AXA_capstone_data" / "policy_handbook")
    HANDBOOK_VECTOR_DB_DIR: str = str(PROJECT_ROOT / "data" / "handbook_vector_store")
    HANDBOOK_VECTOR_COLLECTION: str = "axa_insurance_handbook"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
