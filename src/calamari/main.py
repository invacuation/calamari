import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from calamari.octopus import OctopusClient
from calamari.state import load_state, load_tokens, save_state, save_tokens
from calamari.tado import TadoClient

logger = logging.getLogger(__name__)

REQUIRED_ENV = ["OCTOPUS_API_KEY", "OCTOPUS_ACCOUNT_NUMBER"]

MAX_RETRY_INTERVAL = 3600  # 1 hour
MAX_RETRY_WINDOW = 21600  # 6 hours


def load_config() -> dict:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    return {
        "octopus_api_key": os.environ["OCTOPUS_API_KEY"],
        "octopus_account_number": os.environ["OCTOPUS_ACCOUNT_NUMBER"],
        "tado_home_id": os.environ.get("TADO_HOME_ID"),
        "tado_token_file": os.environ.get("TADO_TOKEN_FILE", "/data/tado_tokens.json"),
        "state_file": os.environ.get("STATE_FILE", "/data/state.json"),
        "submit_on_startup": os.environ.get("SUBMIT_ON_STARTUP", "").lower()
        in ("true", "1", "yes"),
    }


def retry_with_backoff(
    action,
    initial_delay: int = 60,
    max_delay: int = MAX_RETRY_INTERVAL,
    max_window: int = MAX_RETRY_WINDOW,
):
    start = time.monotonic()
    delay = initial_delay

    while True:
        try:
            return action()
        except Exception as e:
            elapsed = time.monotonic() - start
            if elapsed >= max_window:
                logger.error("Retry window exhausted after %ds: %s", int(elapsed), e)
                return None
            logger.warning("Attempt failed: %s. Retrying in %ds", e, delay)
            time.sleep(delay)
            delay = min(delay * 2, max_delay) if max_delay > 0 else 0


SUBMIT_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]


def seconds_until_next_submit(now: datetime | None = None) -> tuple[int, int]:
    now = now or datetime.now()
    for hour in SUBMIT_HOURS:
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target > now:
            return int((target - now).total_seconds()), hour
    # All hours today have passed, next is midnight tomorrow
    target = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((target - now).total_seconds()), 0


_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down", signum)
    _shutdown = True


def try_submit(
    octopus: OctopusClient,
    tado: TadoClient,
    meter_id: str,
    state: dict,
    state_path: Path,
) -> None:
    if not octopus.check_rate_limit():
        logger.warning("Octopus rate limited, will retry next cycle")
        return

    try:
        tado.refresh()
    except RuntimeError as e:
        logger.error("Tado token refresh failed, skipping cycle: %s", e)
        return

    reading = octopus.get_latest_reading(meter_id)
    if not reading:
        logger.warning("No reading available from Octopus")
        return

    reading_date = reading["read_at"].split("T")[0]
    logger.info("Got reading: %d (read at %s)", reading["value"], reading["read_at"])

    def submit():
        tado.submit_reading(date=reading_date, reading=reading["value"])
        return True

    result = retry_with_backoff(submit)
    if result:
        state["last_submission_date"] = reading_date
        state["last_reading_value"] = reading["value"]
        save_state(state_path, state)
    else:
        logger.error("Failed to submit reading after retries")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config()
    state_path = Path(config["state_file"])
    token_path = Path(config["tado_token_file"])

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    octopus = OctopusClient(
        api_key=config["octopus_api_key"],
        account_number=config["octopus_account_number"],
    )
    tado = TadoClient(
        home_id=config["tado_home_id"],
        on_tokens_refreshed=lambda tokens: save_tokens(token_path, tokens),
    )

    # Authenticate Octopus
    octopus.authenticate()
    meter_info = octopus.get_meter_info()
    meter_id = meter_info["meter_id"]
    logger.info(
        "Found gas meter: MPRN=%s, serial=%s",
        meter_info["mprn"],
        meter_info["serial_number"],
    )

    # Authenticate Tado
    tokens = load_tokens(token_path)
    if tokens and tokens.get("refresh_token"):
        try:
            tado.refresh_access_token(tokens["refresh_token"])
            logger.info("Tado token refresh successful")
        except RuntimeError:
            logger.warning("Tado token refresh failed, starting device auth")
            tokens = None

    if not tokens:
        device_data = tado.start_device_auth()
        logger.info("Waiting for user to authenticate...")
        new_tokens = tado.poll_device_auth(device_data["device_code"])
        save_tokens(token_path, new_tokens)

    # Resolve home ID (auto-detect if not provided)
    tado.get_home_id()

    # Main loop
    state = load_state(state_path)

    if config["submit_on_startup"]:
        logger.info("SUBMIT_ON_STARTUP is set, submitting immediately")
        try_submit(octopus, tado, meter_id, state, state_path)

    logger.info(
        "Entering main loop. Submit schedule: %s",
        ", ".join(f"{h:02d}:00" for h in SUBMIT_HOURS),
    )

    while not _shutdown:
        wait, next_hour = seconds_until_next_submit()
        logger.info("Sleeping %d seconds until %02d:00", wait, next_hour)

        sleep_end = time.monotonic() + wait
        while time.monotonic() < sleep_end and not _shutdown:
            time.sleep(min(60, sleep_end - time.monotonic()))

        if _shutdown:
            break

        try_submit(octopus, tado, meter_id, state, state_path)

    logger.info("Shutdown complete")
