import os
from datetime import datetime
from unittest.mock import patch

import pytest

from calamari.main import load_config, retry_with_backoff, seconds_until_hour


def test_load_config_all_set():
    env = {
        "OCTOPUS_API_KEY": "sk_live_test",
        "OCTOPUS_ACCOUNT_NUMBER": "A-1234",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config["octopus_api_key"] == "sk_live_test"
    assert config["octopus_account_number"] == "A-1234"
    assert config["tado_home_id"] is None
    assert config["submit_hour"] == 21
    assert config["tado_token_file"] == "/data/tado_tokens.json"
    assert config["state_file"] == "/data/state.json"
    assert config["submit_on_startup"] is False


def test_load_config_with_tado_home_id():
    env = {
        "OCTOPUS_API_KEY": "sk_live_test",
        "OCTOPUS_ACCOUNT_NUMBER": "A-1234",
        "TADO_HOME_ID": "12345",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config["tado_home_id"] == "12345"


def test_load_config_submit_on_startup():
    env = {
        "OCTOPUS_API_KEY": "sk_live_test",
        "OCTOPUS_ACCOUNT_NUMBER": "A-1234",
        "SUBMIT_ON_STARTUP": "true",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config["submit_on_startup"] is True


def test_load_config_custom_values():
    env = {
        "OCTOPUS_API_KEY": "sk_live_test",
        "OCTOPUS_ACCOUNT_NUMBER": "A-1234",
        "TADO_HOME_ID": "12345",
        "SUBMIT_HOUR": "18",
        "TADO_TOKEN_FILE": "/tmp/tokens.json",
        "STATE_FILE": "/tmp/state.json",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config["submit_hour"] == 18
    assert config["tado_token_file"] == "/tmp/tokens.json"
    assert config["state_file"] == "/tmp/state.json"


def test_load_config_missing_required():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            load_config()


def test_seconds_until_hour_future_today():
    # At 14:00, waiting for 21:00 = 7 hours
    now = datetime(2026, 4, 29, 14, 0, 0)
    result = seconds_until_hour(21, now=now)
    assert result == 7 * 3600


def test_seconds_until_hour_past_today():
    # At 22:00, waiting for 21:00 = 23 hours (tomorrow)
    now = datetime(2026, 4, 29, 22, 0, 0)
    result = seconds_until_hour(21, now=now)
    assert result == 23 * 3600


def test_seconds_until_hour_exact():
    # At exactly 21:00, next is tomorrow = 24 hours
    now = datetime(2026, 4, 29, 21, 0, 0)
    result = seconds_until_hour(21, now=now)
    assert result == 24 * 3600


def test_retry_with_backoff_succeeds_first_try():
    calls = []

    def action():
        calls.append(1)
        return "ok"

    result = retry_with_backoff(action)
    assert result == "ok"
    assert len(calls) == 1


def test_retry_with_backoff_succeeds_after_retries():
    attempts = []

    def action():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("fail")
        return "ok"

    result = retry_with_backoff(action, initial_delay=0, max_delay=0, max_window=10)
    assert result == "ok"
    assert len(attempts) == 3


def test_retry_with_backoff_exhausted():
    def action():
        raise RuntimeError("always fails")

    result = retry_with_backoff(action, initial_delay=0, max_delay=0, max_window=0)
    assert result is None
