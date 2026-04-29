import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_STATE = {"last_submission_date": None, "last_reading_value": None}


def load_state(path: Path) -> dict:
    if not path.exists():
        logger.info("No state file found at %s, starting fresh", path)
        return dict(_DEFAULT_STATE)
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load state from %s: %s. Starting fresh.", path, e)
        return dict(_DEFAULT_STATE)


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with open(tmp_fd, "w") as f:
            json.dump(state, f)
        Path(tmp_path).replace(path)
        logger.debug("State saved to %s", path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def load_tokens(path: Path) -> dict | None:
    if not path.exists():
        logger.info("No token file found at %s", path)
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load tokens from %s: %s", path, e)
        return None


def save_tokens(path: Path, tokens: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with open(tmp_fd, "w") as f:
            json.dump(tokens, f)
        Path(tmp_path).replace(path)
        logger.debug("Tokens saved to %s", path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
