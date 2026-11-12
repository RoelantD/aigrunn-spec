"""Application settings and run configuration.

Secrets are held as ``SecretStr`` and only unwrapped at the HTTP boundary (Constitution II).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.security import validate_service_url

APP_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT.parent / "aps-data"
REPO_URL_DEFAULT = "https://github.com/your-org/agentic-puzzle-solver"


def _env_files() -> tuple[Path, ...]:
    explicit = os.environ.get("APS_ENV_FILE")
    if explicit:
        return (Path(explicit),)
    return (REPO_ROOT / ".env",)


Effort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]


class RunConfig(BaseModel):
    """Per-run limits and model policy (FR-004). Snapshotted into each run."""

    max_attempts_per_part: int = Field(6, ge=1, le=20)
    escalate_after_failures: int = Field(3, ge=0, le=20)
    escalate_on_timeout: bool = True
    max_submissions_per_part: int = Field(3, ge=1, le=10)
    exec_timeout_s: int = Field(30, ge=5, le=220)
    exec_timeout_max_s: int = Field(120, ge=5, le=220)
    max_spend_usd: float = Field(20.0, ge=0)
    aoc_min_interval_s: float = Field(5.0, ge=1.0, le=120.0)
    workhorse_efforts: list[Effort] = Field(default_factory=lambda: ["medium", "medium", "high"])
    escalation_effort: Effort = "high"
    max_output_tokens: int = Field(32000, ge=1024, le=128000)

    @model_validator(mode="after")
    def _check(self) -> RunConfig:
        if self.exec_timeout_s > self.exec_timeout_max_s:
            raise ValueError("exec_timeout_s must not exceed exec_timeout_max_s")
        if not self.workhorse_efforts:
            raise ValueError("workhorse_efforts must not be empty")
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_files(), env_file_encoding="utf-8", extra="ignore")

    # Runtime
    aps_data_dir: Path = DEFAULT_DATA_DIR
    aps_host: str = "127.0.0.1"
    aps_port: int = 8765
    aps_cors_origins: str = "http://127.0.0.1:5175,http://localhost:5175"
    aps_log_level: str = "INFO"
    aps_repo_url: str = REPO_URL_DEFAULT

    # Advent of Code (backend only)
    aoc_session: SecretStr | None = None
    aoc_contact: str = ""
    aoc_min_interval_s: float = Field(5.0, ge=1.0)

    # Microsoft Foundry - workhorse (OpenAI Responses API, v1)
    foundry_openai_base_url: str | None = None  # https://<res>.openai.azure.com/openai/v1
    workhorse_deployment: str = "gpt-6.1-sol"
    workhorse_display_name: str = "GPT-6.1 Sol"
    foundry_openai_api_key: SecretStr | None = None

    # Microsoft Foundry - escalation (Claude Messages API)
    foundry_anthropic_base_url: str | None = None  # https://<res>.services.ai.azure.com/anthropic
    escalation_deployment: str = "claude-opus-5-5"
    escalation_display_name: str = "Claude Opus 5.5"
    foundry_anthropic_api_key: SecretStr | None = None

    foundry_token_scope: str = "https://ai.azure.com/.default"  # noqa: S105 - OAuth scope, not a secret

    # Azure Container Apps Dynamic Sessions
    sessions_pool_endpoint: str | None = None
    sessions_api_version: str = "2025-10-02-preview"
    sessions_token_scope: str = "https://dynamicsessions.io/.default"  # noqa: S105 - OAuth scope

    # Pricing in USD per 1M tokens (configurable; verify current prices - not hardcoded facts)
    workhorse_price_input_per_mtok: float = 0.0
    workhorse_price_output_per_mtok: float = 0.0
    escalation_price_input_per_mtok: float = 0.0
    escalation_price_output_per_mtok: float = 0.0

    # Defaults for new runs
    default_max_spend_usd: float = 20.0

    @field_validator("aps_data_dir")
    @classmethod
    def _resolve_data_dir(cls, v: Path) -> Path:
        # Relative paths are relative to the repository root (not the process cwd).
        return v if v.is_absolute() else (REPO_ROOT / v).resolve()

    @field_validator("foundry_openai_base_url", "foundry_anthropic_base_url", "sessions_pool_endpoint")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "" or "<" in v:  # empty or still the .env.example placeholder
            return None
        return validate_service_url(v.strip()).rstrip("/")

    @property
    def db_path(self) -> Path:
        return self.aps_data_dir / "solver.db"

    @property
    def cache_dir(self) -> Path:
        return self.aps_data_dir / "cache"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.aps_cors_origins.split(",") if o.strip()]

    def secret_values(self) -> list[str]:
        """All configured secret strings, used by the log/event redaction layer."""
        out = []
        for s in (self.aoc_session, self.foundry_openai_api_key, self.foundry_anthropic_api_key):
            if s is not None and s.get_secret_value():
                out.append(s.get_secret_value())
        return out

    def default_run_config(self) -> RunConfig:
        return RunConfig(aoc_min_interval_s=self.aoc_min_interval_s, max_spend_usd=self.default_max_spend_usd)

    def public_summary(self) -> dict:
        """Non-secret view for the UI: only booleans for credentials."""
        return {
            "version": APP_VERSION,
            "data_dir": str(self.aps_data_dir),
            "aoc_session_configured": self.aoc_session is not None,
            "aoc_contact_configured": bool(self.aoc_contact),
            "workhorse": {
                "display_name": self.workhorse_display_name,
                "deployment": self.workhorse_deployment,
                "configured": self.foundry_openai_base_url is not None,
                "auth": "api-key" if self.foundry_openai_api_key else "entra",
                "priced": self.workhorse_price_input_per_mtok > 0 or self.workhorse_price_output_per_mtok > 0,
            },
            "escalation": {
                "display_name": self.escalation_display_name,
                "deployment": self.escalation_deployment,
                "configured": self.foundry_anthropic_base_url is not None,
                "auth": "api-key" if self.foundry_anthropic_api_key else "entra",
                "priced": self.escalation_price_input_per_mtok > 0 or self.escalation_price_output_per_mtok > 0,
            },
            "sandbox": {"configured": self.sessions_pool_endpoint is not None, "kind": "azure-dynamic-sessions"},
            "run_defaults": self.default_run_config().model_dump(),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
