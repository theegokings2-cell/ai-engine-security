"""
Configuration settings for Office Manager API.
Loads from environment variables with Pydantic validation.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    APP_ENV: str = Field(default="development", alias="APP_ENV")
    DEBUG: bool = Field(default=False, alias="DEBUG")
    SECRET_KEY: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/office_manager",
        alias="DATABASE_URL",
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    
    # JWT
    JWT_SECRET_KEY: str = Field(default="your-jwt-secret-key", alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # AI Provider Configuration
    # Supports: "openai", "anthropic" (also works with MiniMax), "ollama" (free local LLM)
    AI_PROVIDER: str = Field(default="openai", alias="AI_PROVIDER")

    # OpenAI (or OpenAI-compatible provider)
    OPENAI_API_KEY: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )

    # Anthropic (or Anthropic-compatible provider like MiniMax)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    ANTHROPIC_BASE_URL: Optional[str] = Field(default=None, alias="ANTHROPIC_BASE_URL")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")

    # Ollama (local LLM - free, no API key needed)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    
    # Microsoft Graph
    MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None, alias="MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None, alias="MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID: Optional[str] = Field(default=None, alias="MICROSOFT_TENANT_ID")
    
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: Optional[str] = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")
    
    # Path configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
