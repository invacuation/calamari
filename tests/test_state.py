import json

from calamari.state import load_state, load_tokens, save_state, save_tokens


def test_load_state_missing_file(tmp_path):
    path = tmp_path / "state.json"
    state = load_state(path)
    assert state == {"last_submission_date": None, "last_reading_value": None}


def test_save_and_load_state(tmp_path):
    path = tmp_path / "state.json"
    state = {"last_submission_date": "2026-04-28", "last_reading_value": 12345}
    save_state(path, state)
    loaded = load_state(path)
    assert loaded == state


def test_save_state_atomic_write(tmp_path):
    path = tmp_path / "state.json"
    state = {"last_submission_date": "2026-04-28", "last_reading_value": 12345}
    save_state(path, state)
    # File should exist at the expected path, not a temp file
    assert path.exists()
    assert json.loads(path.read_text()) == state


def test_load_state_corrupted_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not json")
    state = load_state(path)
    assert state == {"last_submission_date": None, "last_reading_value": None}


def test_load_tokens_missing_file(tmp_path):
    path = tmp_path / "tokens.json"
    tokens = load_tokens(path)
    assert tokens is None


def test_save_and_load_tokens(tmp_path):
    path = tmp_path / "tokens.json"
    tokens = {
        "access_token": "abc",
        "refresh_token": "def",
        "expires_in": 1800,
    }
    save_tokens(path, tokens)
    loaded = load_tokens(path)
    assert loaded == tokens


def test_load_tokens_corrupted_file(tmp_path):
    path = tmp_path / "tokens.json"
    path.write_text("{bad")
    tokens = load_tokens(path)
    assert tokens is None
