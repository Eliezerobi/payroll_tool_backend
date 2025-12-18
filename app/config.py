from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str
    ALLOWED_ORIGINS: str = "http://localhost:5173"
        # add these 3
    HELLONOTE_EMAIL: str | None = None
    HELLONOTE_PASSWORD: str | None = None
    POWER_AUTOMATE_MYSELF: str | None = None
    POWER_AUTOMATE_DAILY_REPORT: str | None = None
    CHHA_INSURANCES: List[str] = Field(default_factory=list)

    # Add these so your .env doesn't crash startup
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None



    
    MONDAY_API_KEY: str | None = None


    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
