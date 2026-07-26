from typing import Any

import pytest
import requests
from src.binance.base_client import BaseClientRest


# Minimal fake HTTP response.
class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        text: str = "{}",
        payload: Any = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.payload = payload if payload is not None else {}
        self.raise_for_status_called = False

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True
        raise RuntimeError("Fake HTTP error")


# Minimal fake requests session.
class FakeSession:
    def __init__(
        self,
        response: FakeResponse | None = None,
        exception: requests.RequestException | None = None,
    ) -> None:
        self.response = response
        self.exception = exception
        self.last_request: dict[str, Any] | None = None

    def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> FakeResponse:
        self.last_request = {
            "method": method,
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        }

        if self.exception is not None:
            raise self.exception

        if self.response is None:
            raise RuntimeError("FakeSession requires response or exception")

        return self.response


def create_base_client() -> BaseClientRest:
    return BaseClientRest(
        base_url="https://api.binance.com/api/",
        timeout_seconds=7,
        api_key="fake_key",
        api_secret="fake_secret",
    )


def test_base_client_strips_trailing_slash() -> None:
    client = create_base_client()

    assert client.base_url == "https://api.binance.com/api"
    assert client.timeout_seconds == 7
    assert client.api_key == "fake_key"
    assert client.api_secret == "fake_secret"


def test_base_client_request_returns_json_dict() -> None:
    client = create_base_client()

    fake_session = FakeSession(
        response=FakeResponse(
            status_code=200,
            text='{"serverTime": 123}',
            payload={"serverTime": 123},
        )
    )

    client.session = fake_session

    data = client._request(
        method="GET",
        path="/v3/time",
        params={"symbol": "BTCUSDT"},
    )

    assert data == {"serverTime": 123}
    assert fake_session.last_request is not None
    assert fake_session.last_request["method"] == "GET"
    assert fake_session.last_request["url"] == ("https://api.binance.com/api/v3/time")
    assert fake_session.last_request["params"] == {"symbol": "BTCUSDT"}
    assert fake_session.last_request["headers"] is None
    assert fake_session.last_request["timeout"] == 7


def test_base_client_request_returns_json_list() -> None:
    client = create_base_client()

    fake_session = FakeSession(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    client.session = fake_session

    data = client._request(
        method="GET",
        path="/v3/openOrders",
    )

    assert data == []


def test_base_client_request_returns_empty_dict_for_empty_body() -> None:
    client = create_base_client()

    fake_session = FakeSession(
        response=FakeResponse(
            status_code=200,
            text="",
            payload=None,
        )
    )

    client.session = fake_session

    data = client._request(
        method="GET",
        path="/v3/ping",
    )

    assert data == {}


def test_base_client_request_raises_for_http_error() -> None:
    client = create_base_client()

    response = FakeResponse(
        status_code=400,
        text='{"code": -1100, "msg": "Bad request"}',
        payload={"code": -1100, "msg": "Bad request"},
    )

    fake_session = FakeSession(response=response)
    client.session = fake_session

    with pytest.raises(RuntimeError):
        client._request(
            method="GET",
            path="/v3/order",
        )

    assert response.raise_for_status_called is True


def test_base_client_request_reraises_request_exception() -> None:
    client = create_base_client()

    fake_session = FakeSession(
        exception=requests.ConnectionError("Fake connection error")
    )

    client.session = fake_session

    with pytest.raises(requests.ConnectionError):
        client._request(
            method="GET",
            path="/v3/time",
        )

    assert fake_session.last_request is not None
    assert fake_session.last_request["method"] == "GET"
    assert fake_session.last_request["url"].endswith("/v3/time")


def test_base_client_sign_returns_expected_hmac() -> None:
    client = create_base_client()

    signature = client._sign(query_string="symbol=BTCUSDT&timestamp=1700000000000")

    assert signature == (
        "5078ee788e711bb5afb87f622de053e9861c9a6bc8113c671b4406e2d77e0e39"
    )


def test_base_client_signed_request_adds_authentication_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.binance.base_client.time.time",
        lambda: 1_700_000_000.0,
    )

    client = create_base_client()

    fake_session = FakeSession(
        response=FakeResponse(
            status_code=200,
            text='{"orderId": 123}',
            payload={"orderId": 123},
        )
    )

    client.session = fake_session

    data = client._signed_request(
        method="GET",
        path="/v3/order",
        params={"symbol": "BTCUSDT"},
    )

    request = fake_session.last_request

    assert request is not None
    assert data == {"orderId": 123}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/order")

    assert request["headers"] == {
        "X-MBX-APIKEY": "fake_key",
    }

    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["timestamp"] == 1_700_000_000_000
    assert request["params"]["recvWindow"] == 5000
    assert request["params"]["signature"] == (
        "5e9755092be91bebe1df424feb30df49f8f91cdf866e48c99677be47cc897191"
    )


def test_base_client_signed_request_requires_api_key() -> None:
    client = BaseClientRest(
        base_url="https://api.binance.com/api",
        api_key=None,
        api_secret="fake_secret",
    )

    with pytest.raises(ValueError):
        client._signed_request(
            method="GET",
            path="/v3/account",
        )


def test_base_client_signed_request_requires_api_secret() -> None:
    client = BaseClientRest(
        base_url="https://api.binance.com/api",
        api_key="fake_key",
        api_secret=None,
    )

    with pytest.raises(ValueError):
        client._signed_request(
            method="GET",
            path="/v3/account",
        )


def test_base_client_sign_requires_credentials() -> None:
    client = BaseClientRest(
        base_url="https://api.binance.com/api",
        api_key="fake_key",
        api_secret=None,
    )

    with pytest.raises(ValueError):
        client._sign(query_string="symbol=BTCUSDT")
