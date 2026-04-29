import httpx
import pytest
import respx

from calamari.tado import TadoClient

TOKEN_URL = "https://login.tado.com/oauth2/token"
DEVICE_AUTH_URL = "https://login.tado.com/oauth2/device_authorize"
API_BASE = "https://my.tado.com/api/v2"
EIQ_BASE = "https://energy-insights.tado.com/api"


@respx.mock
def test_get_home_id_auto_detect():
    respx.get(f"{API_BASE}/me").mock(
        return_value=httpx.Response(
            200,
            json={"homes": [{"id": 98765, "name": "My Home"}]},
        )
    )

    client = TadoClient()
    client._access_token = "access-123"
    home_id = client.get_home_id()

    assert home_id == "98765"
    assert client._home_id == "98765"


def test_get_home_id_provided():
    client = TadoClient(home_id="12345")
    home_id = client.get_home_id()
    assert home_id == "12345"


@respx.mock
def test_get_home_id_no_homes():
    respx.get(f"{API_BASE}/me").mock(
        return_value=httpx.Response(200, json={"homes": []})
    )

    client = TadoClient()
    client._access_token = "access-123"
    with pytest.raises(RuntimeError, match="No homes found"):
        client.get_home_id()


@respx.mock
def test_refresh_token_success():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 1800,
            },
        )
    )

    client = TadoClient(home_id="12345")
    result = client.refresh_access_token("old-refresh")

    assert result["access_token"] == "new-access"
    assert result["refresh_token"] == "new-refresh"
    assert client._access_token == "new-access"


@respx.mock
def test_refresh_token_failure():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )

    client = TadoClient(home_id="12345")
    with pytest.raises(RuntimeError, match="Failed to refresh Tado token"):
        client.refresh_access_token("expired-refresh")


@respx.mock
def test_start_device_auth():
    respx.post(DEVICE_AUTH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "device_code": "dev-code-123",
                "user_code": "ABCD-1234",
                "verification_uri": "https://login.tado.com/activate",
                "expires_in": 300,
                "interval": 5,
            },
        )
    )

    client = TadoClient(home_id="12345")
    result = client.start_device_auth()

    assert result["device_code"] == "dev-code-123"
    assert result["user_code"] == "ABCD-1234"


@respx.mock
def test_poll_device_auth_pending_then_success():
    route = respx.post(TOKEN_URL)
    route.side_effect = [
        httpx.Response(400, json={"error": "authorization_pending"}),
        httpx.Response(
            200,
            json={
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 1800,
            },
        ),
    ]

    client = TadoClient(home_id="12345")
    result = client.poll_device_auth("dev-code-123", interval=0)

    assert result["access_token"] == "access-123"
    assert client._access_token == "access-123"


@respx.mock
def test_poll_device_auth_expired():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(400, json={"error": "expired_token"})
    )

    client = TadoClient(home_id="12345")
    with pytest.raises(RuntimeError, match="Device auth failed"):
        client.poll_device_auth("dev-code-123", interval=0)


@respx.mock
def test_submit_new_reading():
    respx.get(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(200, json={"readings": []})
    )
    respx.post(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "uuid-1",
                "homeId": 12345,
                "reading": 12345,
                "date": "2026-04-28",
            },
        )
    )

    client = TadoClient(home_id="12345")
    client._access_token = "access-123"
    client.submit_reading(date="2026-04-28", reading=12345)


@respx.mock
def test_submit_reading_updates_existing():
    respx.get(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(
            200,
            json={"readings": [{"id": "uuid-1", "date": "2026-04-28", "reading": 100}]},
        )
    )
    route = respx.put(f"{EIQ_BASE}/homes/12345/meterReadings/uuid-1").mock(
        return_value=httpx.Response(200, json={})
    )

    client = TadoClient(home_id="12345")
    client._access_token = "access-123"
    client.submit_reading(date="2026-04-28", reading=12345)

    assert route.called


@respx.mock
def test_submit_reading_skips_if_same_value():
    respx.get(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(
            200,
            json={
                "readings": [{"id": "uuid-1", "date": "2026-04-28", "reading": 12345}]
            },
        )
    )

    client = TadoClient(home_id="12345")
    client._access_token = "access-123"
    client.submit_reading(date="2026-04-28", reading=12345)


@respx.mock
def test_submit_reading_rate_limited():
    respx.get(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(200, json={"readings": []})
    )
    respx.post(f"{EIQ_BASE}/homes/12345/meterReadings").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "60"})
    )

    client = TadoClient(home_id="12345")
    client._access_token = "access-123"
    with pytest.raises(RuntimeError, match="Rate limited"):
        client.submit_reading(date="2026-04-28", reading=12345)
