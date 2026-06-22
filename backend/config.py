from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "S.at8637423550"
    DB_NAME: str = "monika_g_cafe"

    # JWT
    SECRET_KEY: str = "This-is-my-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "Monika G Cafe Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Upload
    UPLOAD_DIR: str = "static/images/uploads"
    MAX_FILE_SIZE_MB: int = 5

    # GST
    DEFAULT_GST_PERCENT: float = 5.0

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Twilio
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = "dc93faedf66eaca1c10064665df25e39"
    TWILIO_PHONE_NUMBER: str = "+918637423550"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "sugumarperumalr@gmail.com"
    SMTP_PASSWORD: str = "lujj jxlx alei tztu"
    FROM_EMAIL: str = "sugumarperumalr@gmail.com"
    FROM_NAME: str = "Monika G Cafe"

    # Loyalty
    POINTS_PER_RUPEE: int = 1
    POINTS_REDEEM_RATE: float = 0.10

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()