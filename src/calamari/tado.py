import logging
import time

import httpx

logger = logging.getLogger(__name__)

CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"
AUTH_BASE = "https://login.tado.com/oauth2"
API_BASE = "https://my.tado.com/api/v2"
EIQ_BASE = "https://energy-insights.tado.com/api"


class TadoClient:
    def __init__(self, home_id: str | None = None):
        self._home_id = home_id
        self._access_token: str | None = None
        self._http = httpx.Client(timeout=30)

    def get_home_id(self) -> str:
        if self._home_id:
            return self._home_id
        logger.info("Fetching Tado home ID from account")
        response = self._http.get(
            f"{API_BASE}/me",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        homes = response.json()["homes"]
        if not homes:
            raise RuntimeError("No homes found in Tado account")
        self._home_id = str(homes[0]["id"])
        logger.info("Found Tado home ID: %s", self._home_id)
        return self._home_id

    def refresh_access_token(self, refresh_token: str) -> dict:
        logger.info("Refreshing Tado access token")
        response = self._http.post(
            f"{AUTH_BASE}/token",
            params={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.status_code != 200:
            logger.error("Failed to refresh Tado token: %s", response.text)
            raise RuntimeError("Failed to refresh Tado token")

        data = response.json()
        self._access_token = data["access_token"]
        logger.info("Tado token refreshed successfully")
        return data

    def start_device_auth(self) -> dict:
        logger.info("Starting Tado device authorization flow")
        response = self._http.post(
            f"{AUTH_BASE}/device_authorize",
            params={"client_id": CLIENT_ID, "scope": "offline_access"},
        )
        if response.status_code != 200:
            logger.error("Device auth request failed: %s", response.text)
            response.raise_for_status()
        data = response.json()
        verification_uri = data["verification_uri"]
        user_code = data["user_code"]
        url = f"{verification_uri}?userCode={user_code}&client_id={CLIENT_ID}"
        logger.info("")
        logger.info("============================================")
        logger.info("  TADO AUTHENTICATION REQUIRED")
        logger.info("  Visit this URL to log in:")
        logger.info("  %s", url)
        logger.info("============================================")
        logger.info("")
        return data

    def poll_device_auth(self, device_code: str, interval: int = 5) -> dict:
        while True:
            response = self._http.post(
                f"{AUTH_BASE}/token",
                params={
                    "client_id": CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                logger.info("Device authorization successful")
                return data

            body = response.json()
            if body.get("error") == "authorization_pending":
                logger.info(
                    "Waiting for authentication... (polling again in %ds)", interval
                )
                time.sleep(interval)
                continue

            logger.error("Device auth failed: %s", body)
            raise RuntimeError(f"Device auth failed: {body.get('error')}")

    def submit_reading(self, date: str, reading: int) -> None:
        logger.info("Submitting reading %d for date %s to Tado", reading, date)
        response = self._http.post(
            f"{EIQ_BASE}/homes/{self._home_id}/meterReadings",
            headers={"Authorization": f"Bearer {self._access_token}"},
            json={"date": date, "reading": reading},
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            logger.warning("Rate limited by Tado. Retry-After: %s", retry_after)
            raise RuntimeError(f"Rate limited by Tado (retry after {retry_after}s)")
        if not response.is_success:
            logger.error(
                "Tado submission failed (%d): %s",
                response.status_code,
                response.text,
            )
        response.raise_for_status()
        logger.info("Reading submitted successfully")
