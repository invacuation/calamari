import os
from datetime import datetime
from unittest.mock import patch

import pytest

from calamari.main import load_config, retry_with_backoff, seconds_until_next_submit


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
        "TADO_TOKEN_FILE": "/tmp/tokens.json",
        "STATE_FILE": "/tmp/state.json",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config["tado_token_file"] == "/tmp/tokens.json"
    assert config["state_file"] == "/tmp/state.json"


def test_load_config_missing_required():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            load_config()


def test_seconds_until_next_submit_between_slots():
    # At 14:00, next slot is 15:00 = 1 hour
    now = datetime(2026, 4, 29, 14, 0, 0)
    seconds, hour = seconds_until_next_submit(now=now)
    assert seconds == 3600
    assert hour == 15


def test_seconds_until_next_submit_just_after_slot():
    # At 09:01, next slot is 12:00 = 2h59m
    now = datetime(2026, 4, 29, 9, 1, 0)
    seconds, hour = seconds_until_next_submit(now=now)
    assert seconds == 2 * 3600 + 59 * 60
    assert hour == 12


def test_seconds_until_next_submit_after_last_slot():
    # At 22:00, next slot is 00:00 tomorrow = 2 hours
    now = datetime(2026, 4, 29, 22, 0, 0)
    seconds, hour = seconds_until_next_submit(now=now)
    assert seconds == 2 * 3600
    assert hour == 0


def test_seconds_until_next_submit_exactly_on_slot():
    # At exactly 09:00, next slot is 12:00 = 3 hours
    now = datetime(2026, 4, 29, 9, 0, 0)
    seconds, hour = seconds_until_next_submit(now=now)
    assert seconds == 3 * 3600
    assert hour == 12


def test_seconds_until_next_submit_just_before_midnight():
    # At 23:59, next slot is 00:00 = 1 minute
    now = datetime(2026, 4, 29, 23, 59, 0)
    seconds, hour = seconds_until_next_submit(now=now)
    assert seconds == 60
    assert hour == 0


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
