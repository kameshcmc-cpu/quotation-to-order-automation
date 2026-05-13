import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    OWNER_TELEGRAM_CHAT_ID: str = ""

    BUSINESS_NAME: str = "My Business"
    BUSINESS_ADDRESS: str = "123 Main Street, City, State - 400001"
    BUSINESS_PHONE: str = "+91-XXXXXXXXXX"
    BUSINESS_EMAIL: str = "business@example.com"
    BUSINESS_GST: str = "22AAAAA0000A1Z5"
    BUSINESS_LOGO_PATH: Optional[str] = None

    SECRET_KEY: str = "change-this-secret"
    DATABASE_URL: str = "sqlite:////data/quotation_app.db" if os.path.isdir("/data") else "sqlite:///./quotation_app.db"
    API_BASE_URL: str = "http://localhost:8000"

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    DEFAULT_GST_PERCENT: float = 18.0

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
