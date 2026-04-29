import logging
import math

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.octopus.energy/v1/graphql/"

OBTAIN_TOKEN_MUTATION = """
mutation ObtainToken($input: ObtainJSONWebTokenInput!) {
    obtainKrakenToken(input: $input) {
        token
        refreshToken
        refreshExpiresIn
    }
}
"""

GET_METER_INFO_QUERY = """
query GetMeterInfo($accountNumber: String!) {
    account(accountNumber: $accountNumber) {
        gasAgreements(active: true) {
            meterPoint {
                mprn
                meters(includeInactive: false) {
                    id
                    serialNumber
                }
            }
        }
    }
}
"""

GET_LATEST_READING_QUERY = """
query GetLatestReading($accountNumber: String!, $meterId: String!) {
    gasMeterReadings(
        accountNumber: $accountNumber
        meterId: $meterId
        first: 1
    ) {
        edges {
            node {
                readAt
                readingSource
                registers {
                    value
                }
            }
        }
    }
}
"""

RATE_LIMIT_QUERY = """
query GetRateLimitInfo {
    rateLimitInfo {
        pointsAllowanceRateLimit {
            remainingPoints
            isBlocked
        }
    }
}
"""


class OctopusClient:
    def __init__(self, api_key: str, account_number: str):
        self._api_key = api_key
        self._account_number = account_number
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._http = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        logger.info("Authenticating with Octopus Energy API")
        result = self._graphql(
            OBTAIN_TOKEN_MUTATION,
            {"input": {"APIKey": self._api_key}},
            authenticated=False,
        )
        token_data = result["obtainKrakenToken"]
        self._token = token_data["token"]
        self._refresh_token = token_data["refreshToken"]
        logger.info("Authenticated successfully")

    def get_meter_info(self) -> dict:
        logger.info("Fetching gas meter info for account %s", self._account_number)
        result = self._graphql(
            GET_METER_INFO_QUERY,
            {"accountNumber": self._account_number},
        )
        meter_point = result["account"]["gasAgreements"][0]["meterPoint"]
        meter = meter_point["meters"][0]
        return {
            "mprn": meter_point["mprn"],
            "meter_id": meter["id"],
            "serial_number": meter["serialNumber"],
        }

    def get_latest_reading(self, meter_id: str) -> dict | None:
        logger.info("Fetching latest gas meter reading")
        result = self._graphql(
            GET_LATEST_READING_QUERY,
            {"accountNumber": self._account_number, "meterId": meter_id},
        )
        edges = result["gasMeterReadings"]["edges"]
        if not edges:
            logger.warning("No gas meter readings found")
            return None
        node = edges[0]["node"]
        raw_value = float(node["registers"][0]["value"])
        return {
            "read_at": node["readAt"],
            "value": math.floor(raw_value),
        }

    def check_rate_limit(self) -> bool:
        result = self._graphql(RATE_LIMIT_QUERY)
        info = result["rateLimitInfo"]["pointsAllowanceRateLimit"]
        if info["isBlocked"]:
            logger.warning("Octopus API rate limit exceeded")
            return False
        logger.debug(
            "Octopus API rate limit OK: %d points remaining", info["remainingPoints"]
        )
        return True

    def _graphql(
        self, query: str, variables: dict | None = None, authenticated: bool = True
    ) -> dict:
        headers = {}
        if authenticated and self._token:
            headers["Authorization"] = f"JWT {self._token}"

        response = self._http.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            headers=headers,
        )
        response.raise_for_status()
        body = response.json()

        if "errors" in body:
            msg = body["errors"][0]["message"]
            logger.error("GraphQL error: %s", msg)
            raise RuntimeError(msg)

        return body["data"]
