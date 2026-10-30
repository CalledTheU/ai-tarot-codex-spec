# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql+psycopg://tarot:change_me@127.0.0.1:5432/ai_tarot"
        ),
        repr=False,
    )
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai_compatible")
    )
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""), repr=False)
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    llm_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    )
    llm_max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "3000"))
    )

    auth_mode: str = field(default_factory=lambda: os.getenv("AUTH_MODE", "bearer"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    auth_requests_per_minute: int = field(
        default_factory=lambda: int(os.getenv("AUTH_REQUESTS_PER_MINUTE", "20"))
    )
    readings_per_minute: int = field(
        default_factory=lambda: int(os.getenv("READINGS_PER_MINUTE", "10"))
    )
    model_requests_per_minute: int = field(
        default_factory=lambda: int(os.getenv("MODEL_REQUESTS_PER_MINUTE", "5"))
    )
    model_max_concurrency: int = field(
        default_factory=lambda: int(os.getenv("MODEL_MAX_CONCURRENCY", "2"))
    )

    def __post_init__(self):
        if self.auth_mode != "bearer":
            raise ValueError("Only AUTH_MODE=bearer is supported")
        if self.access_token_expire_minutes <= 0 or self.auth_requests_per_minute <= 0:
            raise ValueError("Authentication limits must be positive")
        if (
            min(
                self.readings_per_minute, self.model_requests_per_minute, self.model_max_concurrency
            )
            <= 0
        ):
            raise ValueError("Request and concurrency limits must be positive")
        if self.llm_timeout_seconds <= 0 or self.llm_max_output_tokens <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS and LLM_MAX_OUTPUT_TOKENS must be positive")


settings = Settings()
