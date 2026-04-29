import httpx
import pytest
import respx

from calamari.octopus import OctopusClient

GRAPHQL_URL = "https://api.octopus.energy/v1/graphql/"


@respx.mock
def test_obtain_token():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "obtainKrakenToken": {
                        "token": "jwt-token-123",
                        "refreshToken": "refresh-456",
                        "refreshExpiresIn": 9999999999,
                    }
                }
            },
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client.authenticate()

    assert client._token == "jwt-token-123"
    assert client._refresh_token == "refresh-456"


@respx.mock
def test_obtain_token_failure():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={"errors": [{"message": "Invalid API key"}]},
        )
    )

    client = OctopusClient(api_key="bad-key", account_number="A-1234")
    with pytest.raises(RuntimeError, match="Invalid API key"):
        client.authenticate()


@respx.mock
def test_get_meter_info():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "account": {
                        "gasAgreements": [
                            {
                                "meterPoint": {
                                    "mprn": "1234567890",
                                    "meters": [
                                        {
                                            "id": "42",
                                            "serialNumber": "E6S00000000000",
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                }
            },
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client._token = "jwt-token-123"
    meter_info = client.get_meter_info()

    assert meter_info == {
        "mprn": "1234567890",
        "meter_id": "42",
        "serial_number": "E6S00000000000",
    }


@respx.mock
def test_get_latest_reading():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "gasMeterReadings": {
                        "edges": [
                            {
                                "node": {
                                    "readAt": "2026-04-28T21:00:00+00:00",
                                    "readingSource": "SMART",
                                    "registers": [{"value": "12345.678"}],
                                }
                            }
                        ]
                    }
                }
            },
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client._token = "jwt-token-123"
    reading = client.get_latest_reading(meter_id="42")

    assert reading == {"read_at": "2026-04-28T21:00:00+00:00", "value": 12345}


@respx.mock
def test_get_latest_reading_no_readings():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": {"gasMeterReadings": {"edges": []}}},
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client._token = "jwt-token-123"
    reading = client.get_latest_reading(meter_id="42")

    assert reading is None


@respx.mock
def test_check_rate_limit_ok():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "rateLimitInfo": {
                        "pointsAllowanceRateLimit": {
                            "remainingPoints": 49000,
                            "isBlocked": False,
                        }
                    }
                }
            },
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client._token = "jwt-token-123"
    assert client.check_rate_limit() is True


@respx.mock
def test_check_rate_limit_blocked():
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "rateLimitInfo": {
                        "pointsAllowanceRateLimit": {
                            "remainingPoints": 0,
                            "isBlocked": True,
                        }
                    }
                }
            },
        )
    )

    client = OctopusClient(api_key="sk_live_test", account_number="A-1234")
    client._token = "jwt-token-123"
    assert client.check_rate_limit() is False
