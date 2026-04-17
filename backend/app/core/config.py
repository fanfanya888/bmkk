from __future__ import annotations

from functools import cached_property
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.api_styles import APIStyle, API_STYLE_CHAT_COMPLETIONS, normalize_api_style


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Benchmark Eval Platform"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_access_log: bool = Field(default=False, alias="BACKEND_ACCESS_LOG")
    backend_api_request_log: bool = Field(default=True, alias="BACKEND_API_REQUEST_LOG")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="127.0.0.1", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5431, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="pdf_question_bank", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str | None = Field(default=None, alias="POSTGRES_PASSWORD")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    model_request_timeout_seconds: float = Field(
        default=90.0,
        alias="MODEL_REQUEST_TIMEOUT_SECONDS",
    )
    judge_api_url: str | None = Field(default=None, alias="JUDGE_API_URL")
    judge_api_model: str | None = Field(default=None, alias="JUDGE_API_MODEL")
    judge_api_key: str | None = Field(default=None, alias="JUDGE_API_KEY")
    judge_api_style: APIStyle = Field(
        default=API_STYLE_CHAT_COMPLETIONS,
        alias="JUDGE_API_STYLE",
    )
    judge_request_timeout_seconds: float = Field(
        default=180.0,
        alias="JUDGE_REQUEST_TIMEOUT_SECONDS",
    )
    judge_request_max_retries: int = Field(
        default=1,
        alias="JUDGE_REQUEST_MAX_RETRIES",
        ge=0,
        le=5,
    )

    @field_validator("judge_api_style", mode="before")
    @classmethod
    def normalize_judge_api_style(cls, value: str | None) -> APIStyle:
        return normalize_api_style(value)

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @cached_property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        if not self.postgres_password:
            raise ValueError(
                "Database configuration is incomplete. Set DATABASE_URL or POSTGRES_PASSWORD."
            )

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        db_name = self.postgres_db
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


settings = Settings()
