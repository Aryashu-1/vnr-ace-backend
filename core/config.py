from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # JWT Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_EXPIRE_MINUTES: int

    # Groq LLM
    GROQ_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore extra env vars

settings = Settings()
