# Unit tests for the shared Binance REST base client.
"""
Provide tests for the Binance REST base client.

This module tests request handling, response parsing, HTTP errors, transport
errors, HMAC signing, signed requests, and credential validation.
"""

from typing import Any

import pytest
import requests
from src.binance.base_client import BaseClientRest


# Minimal fake HTTP response.
class FakeResponse:
    """
    A fake HTTP response for testing REST client behavior.

    Attributes:
        status_code (int): Fake HTTP status code.
        text (str): Fake response body text.
        payload (Any): Fake JSON payload.
        raise_for_status_called (bool): Whether raise_for_status was called.
    """

    def __init__(
        self,
        status_code: int = 200,
        text: str = "{}",
        payload: Any = None,
    ) -> None:
        """
        Initialize a fake HTTP response.

        Parameters:
            status_code (int): Fake HTTP status code.
            text (str): Fake response body text.
            payload (Any): Fake JSON payload.
        """
        self.status_code = status_code
        self.text = text
        self.payload = payload if payload is not None else {}
        self.raise_for_status_called = False

    def json(self) -> Any:
        """
        Return the fake JSON payload.

        Returns:
            Any: Fake JSON payload.
        """
        return self.payload

    def raise_for_status(self) -> None:
        """
        Simulate raising an HTTP error.
        """
        self.raise_for_status_called = True
        raise RuntimeError("Fake HTTP error")


# Minimal fake requests session.
class FakeSession:
    """
    A fake requests session for testing REST client requests.

    Attributes:
        response (FakeResponse | None): Fake response to return.
        exception (requests.RequestException | None): Fake exception to raise.
        last_request (dict[str, Any] | None): Last captured request arguments.
    """

    def __init__(
        self,
        response: FakeResponse | None = None,
        exception: requests.RequestException | None = None,
    ) -> None:
        """
        Initialize a fake requests session.

        Parameters:
            response (FakeResponse | None): Fake response to return.
            exception (requests.RequestException | None): Fake exception to raise.
        """
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
        """
        Capture and return a fake HTTP request.

        Parameters:
            method (str): HTTP request method.
            url (str): Request URL.
            params (dict[str, Any] | None): Query parameters.
            headers (dict[str, str] | None): HTTP headers.
            timeout (int | None): Request timeout in seconds.

        Returns:
            FakeResponse: Fake HTTP response.
        """
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
    """
    Create a Binance REST base client for tests.

    Returns:
        BaseClientRest: Configured test client.
    """
    return BaseClientRest(
        base_url="https://api.binance.com/api/",
        timeout_seconds=7,
        api_key="fake_key",
        api_secret="fake_secret",
    )


def test_base_client_strips_trailing_slash() -> None:
    """
    Test that the base client strips trailing slashes from the base URL.
    """
    client = create_base_client()

    assert client.base_url == "https://api.binance.com/api"
    assert client.timeout_seconds == 7
    assert client.api_key == "fake_key"
    assert client.api_secret == "fake_secret"


def test_base_client_request_returns_json_dict() -> None:
    """
    Test that unsigned requests return JSON dictionaries.
    """
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
    """
    Test that unsigned requests return JSON lists.
    """
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
    """
    Test that empty response bodies return an empty dictionary.
    """
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
    """
    Test that HTTP errors call raise_for_status.
    """
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
    """
    Test that transport exceptions are reraised.
    """
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
    """
    Test that HMAC signing returns the expected signature.
    """
    client = create_base_client()

    signature = client._sign(query_string="symbol=BTCUSDT&timestamp=1700000000000")

    assert signature == (
        "5078ee788e711bb5afb87f622de053e9861c9a6bc8113c671b4406e2d77e0e39"
    )


def test_base_client_signed_request_adds_authentication_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that signed requests add authentication parameters.
    """
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
    """
    Test that signed requests require an API key.
    """
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
    """
    Test that signed requests require an API secret.
    """
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
    """
    Test that signing requires API credentials.
    """
    client = BaseClientRest(
        base_url="https://api.binance.com/api",
        api_key="fake_key",
        api_secret=None,
    )

    with pytest.raises(ValueError):
        client._sign(query_string="symbol=BTCUSDT")
