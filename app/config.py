"""Application configuration management using Pydantic BaseSettings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelShield - Real-Time Data Access Anomaly Detection"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security & Auth
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel_shield.db"

    # Real-Time Anomaly Detection Thresholds
    Z_SCORE_THRESHOLD: float = 3.0  # Deviations >= 3.0 sigma flagged
    Z_SCORE_WINDOW_SECONDS: int = 60  # Sliding micro-window for request velocity
    Z_SCORE_MIN_EVENTS: int = 5  # Minimum historical events before applying Z-Score
    GRAPH_FANOUT_THRESHOLD: int = 5  # Max distinct sensitive resources touched within window
    GRAPH_FANOUT_WINDOW_SECONDS: int = 60  # Window for horizontal traversal / fan-out

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_SENSITIVE: str = "60/minute"

    # Simulator Settings
    SIMULATOR_ENABLED_AT_START: bool = True
    SIMULATOR_DEFAULT_DELAY_SECONDS: float = 2.0

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
