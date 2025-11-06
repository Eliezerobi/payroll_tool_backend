from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    ALLOWED_ORIGINS: str = "http://localhost:5173"
        # add these 3
    HELLONOTE_EMAIL: str | None = None
    HELLONOTE_PASSWORD: str | None = None
    POWER_AUTOMATE_URL: str | None = None


    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
