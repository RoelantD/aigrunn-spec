"""Config validation, allowlisting and redaction (T013)."""

import pytest
from pydantic import ValidationError

from app.config import RunConfig, Settings
from app.security import DisallowedURLError, is_allowed_aoc_url, redact_obj, redact_text, validate_service_url


def test_service_url_allowlist():
    assert validate_service_url("https://x.openai.azure.com/openai/v1")
    assert validate_service_url("https://westeurope.dynamicsessions.io/subscriptions/x")
    for bad in ("http://x.openai.azure.com", "https://evil.example.com", "https://u:p@x.openai.azure.com",
                "https://openai.azure.com.evil.com"):
        with pytest.raises(DisallowedURLError):
            validate_service_url(bad)


def test_settings_reject_bad_endpoint(tmp_path):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, aps_data_dir=tmp_path, foundry_openai_base_url="https://attacker.example/v1")


def test_aoc_url_allowlist():
    assert is_allowed_aoc_url("https://adventofcode.com/2024/day/1")
    assert not is_allowed_aoc_url("http://adventofcode.com/2024")
    assert not is_allowed_aoc_url("https://adventofcode.com.evil.io/2024")


def test_redaction():
    secret = "abcdef0123456789session"
    t = redact_text(f"Cookie: session={secret}; other  Authorization: Bearer eyJabc.def x-api-key: k123", [secret])
    assert secret not in t and "eyJabc" not in t and "k123" not in t
    obj = redact_obj({"headers": {"cookie": "session=1", "x": [secret]}}, [secret])
    assert obj["headers"]["cookie"] == "***REDACTED***" and secret not in str(obj)


def test_run_config_bounds():
    with pytest.raises(ValidationError):
        RunConfig(aoc_min_interval_s=0.5)
    with pytest.raises(ValidationError):
        RunConfig(exec_timeout_s=200, exec_timeout_max_s=120)
    with pytest.raises(ValidationError):
        RunConfig(exec_timeout_max_s=300)
    assert RunConfig().max_attempts_per_part == 6


def test_public_summary_has_no_secrets(tmp_path):
    s = Settings(_env_file=None, aps_data_dir=tmp_path, aoc_session="topsecretsessionvalue",
                 foundry_openai_api_key="key-123456789")
    text = str(s.public_summary())
    assert "topsecretsessionvalue" not in text and "key-123456789" not in text
    assert s.public_summary()["aoc_session_configured"] is True
