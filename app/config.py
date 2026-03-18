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
    MONDAY_BOARD_ID_STRIPE: Optional[str] = None  # <-- add this if you want

    # Stripe (ADD THESE)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_SUCCESS_URL: Optional[str] = None  # must include {LEAD_ID}
    STRIPE_CANCEL_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"  # IMPORTANT: prevents crash if you add unrelated env vars

@lru_cache
def get_settings() -> Settings:
    return Settings()
