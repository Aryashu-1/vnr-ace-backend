from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None

    # JWT Auth
    JWT_SECRET_KEY: str = "placeholder_secret_key_change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # LLM keys
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEYS: Optional[str] = None # Comma-separated list of keys
    ENABLE_KEY_ROTATION: bool = True
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # SMTP Settings (Falling back to IMAP env vars if needed)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    
    # Use existing IMAP env vars as defaults
    EMAIL_ACCOUNT: Optional[str] = "aryataduri@gmail.com"
    EMAIL_PASSWORD: Optional[str] = "rxfitsxqslvnqbdu"
    
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    @property
    def mail_user(self) -> Optional[str]:
        return self.SMTP_USER or self.EMAIL_ACCOUNT

    @property
    def mail_password(self) -> Optional[str]:
        return self.SMTP_PASSWORD or self.EMAIL_PASSWORD

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore extra env vars

settings = Settings()
