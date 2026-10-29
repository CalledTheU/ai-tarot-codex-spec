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

    def __post_init__(self):
        if self.llm_timeout_seconds <= 0 or self.llm_max_output_tokens <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS and LLM_MAX_OUTPUT_TOKENS must be positive")


settings = Settings()
