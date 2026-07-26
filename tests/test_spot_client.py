# Unit tests for the Binance Spot REST client.
"""
Provide tests for the Binance Spot REST client.

This module tests public endpoints, signed account requests, order placement,
order-list placement, order queries, cancellations, and account trade queries.
"""

from typing import Any

import pytest
from src.binance.spot_client import SpotClient


# Minimal fake HTTP response.
class FakeResponse:
    """
    A fake HTTP response for testing Spot client behavior.

    Attributes:
        status_code (int): Fake HTTP status code.
        text (str): Fake response body text.
        payload (Any): Fake JSON payload.
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
        raise RuntimeError("Fake HTTP error")


# Minimal fake requests session.
class FakeSession:
    """
    A fake requests session for testing Spot client requests.

    Attributes:
        response (FakeResponse): Fake response to return.
        last_request (dict[str, Any] | None): Last captured request arguments.
    """

    def __init__(self, response: FakeResponse) -> None:
        """
        Initialize a fake requests session.

        Parameters:
            response (FakeResponse): Fake response to return.
        """
        self.response = response
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

        return self.response


def create_client_with_fake_session(
    response: FakeResponse,
    testnet: bool = True,
) -> tuple[SpotClient, FakeSession]:
    """
    Create a Spot client with a fake HTTP session.

    Parameters:
        response (FakeResponse): Fake response to return from the session.
        testnet (bool): Whether to initialize the client in testnet mode.

    Returns:
        tuple[SpotClient, FakeSession]: Spot client and fake session.
    """
    client = SpotClient(
        testnet=testnet,
        api_key="fake_key",
        api_secret="fake_secret",
    )

    fake_session = FakeSession(response=response)
    client.session = fake_session

    return client, fake_session


def assert_signed_request(request: dict[str, Any]) -> None:
    """
    Assert that a request contains Binance signing fields.

    Parameters:
        request (dict[str, Any]): Captured fake request.
    """
    assert request["headers"] == {
        "X-MBX-APIKEY": "fake_key",
    }

    assert request["params"]["recvWindow"] == 5000
    assert "timestamp" in request["params"]
    assert "signature" in request["params"]


def assert_no_request(fake_session: FakeSession) -> None:
    """
    Assert that no HTTP request was sent.

    Parameters:
        fake_session (FakeSession): Fake session to inspect.
    """
    assert fake_session.last_request is None


def test_spot_client_ping_returns_true() -> None:
    """
    Test that Spot ping returns True.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="{}",
            payload={},
        )
    )

    result = client.ping()

    assert result is True
    assert fake_session.last_request is not None
    assert fake_session.last_request["method"] == "GET"
    assert fake_session.last_request["url"].endswith("/v3/ping")
    assert fake_session.last_request["params"] is None


def test_spot_client_get_server_time_returns_integer() -> None:
    """
    Test that Spot server time returns an integer.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"serverTime": 1234567890}',
            payload={"serverTime": 1234567890},
        )
    )

    server_time = client.get_server_time()

    assert server_time == 1234567890
    assert fake_session.last_request is not None
    assert fake_session.last_request["method"] == "GET"
    assert fake_session.last_request["url"].endswith("/v3/time")
    assert fake_session.last_request["params"] is None


def test_spot_client_get_server_time_raises_for_non_integer() -> None:
    """
    Test that Spot server time rejects non-integer values.
    """
    client, _ = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"serverTime": "1234567890"}',
            payload={"serverTime": "1234567890"},
        )
    )

    with pytest.raises(TypeError):
        client.get_server_time()


def test_spot_client_get_account_info_uses_signed_request() -> None:
    """
    Test that Spot account info uses a signed request.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"balances": []}',
            payload={"balances": []},
        )
    )

    account_info = client.get_account_info()

    request = fake_session.last_request

    assert request is not None
    assert account_info == {"balances": []}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/account")
    assert_signed_request(request)


def test_spot_client_place_order_uses_test_order_endpoint() -> None:
    """
    Test that Spot order validation uses the test endpoint.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="{}",
            payload={},
        )
    )

    order = client.place_order(
        params={
            "symbol": "btcusdt",
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": "0.001",
            "price": "50000.00",
        },
        test=True,
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "LIMIT"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "50000.00"
    assert_signed_request(request)


def test_spot_client_place_order_requires_symbol() -> None:
    """
    Test that Spot order placement requires a symbol.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_order(
            params={
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": "25",
            }
        )

    assert_no_request(fake_session)


def test_spot_client_place_order_requires_string_symbol() -> None:
    """
    Test that Spot order placement requires a string symbol.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(TypeError):
        client.place_order(
            params={
                "symbol": 123,
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": "25",
            }
        )

    assert_no_request(fake_session)


def test_spot_client_place_testnet_order_allowed_when_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that real testnet orders are allowed when live trading is disabled.
    """
    monkeypatch.setattr(
        "src.binance.spot_client.ENABLE_TRADING",
        False,
    )

    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderId": 123}',
            payload={"orderId": 123},
        ),
        testnet=True,
    )

    order = client.place_order(
        params={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": "25",
        },
        test=False,
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {"orderId": 123}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_spot_client_place_live_order_raises_when_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that live Spot orders are blocked when trading is disabled.
    """
    monkeypatch.setattr(
        "src.binance.spot_client.ENABLE_TRADING",
        False,
    )

    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(),
        testnet=False,
    )

    with pytest.raises(RuntimeError):
        client.place_order(
            params={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": "25",
            },
            test=False,
        )

    assert_no_request(fake_session)


def test_spot_client_place_live_order_uses_live_order_endpoint_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that enabled real Spot orders use the live order endpoint.
    """
    monkeypatch.setattr(
        "src.binance.spot_client.ENABLE_TRADING",
        True,
    )

    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderId": 123}',
            payload={"orderId": 123},
        )
    )

    order = client.place_order(
        params={
            "symbol": "btcusdt",
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": "25",
        },
        test=False,
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {"orderId": 123}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["type"] == "MARKET"
    assert_signed_request(request)


def test_spot_client_place_limit_order_builds_expected_params() -> None:
    """
    Test that Spot limit orders build the expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_limit_order(
        symbol="btcusdt",
        side="buy",
        quantity="0.001",
        price="50000.00",
        iceberg_qty="0.0005",
        client_order_id=" limit_001 ",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["url"].endswith("/v3/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "LIMIT"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "50000.00"
    assert request["params"]["icebergQty"] == "0.0005"
    assert request["params"]["newClientOrderId"] == "limit_001"
    assert_signed_request(request)


def test_spot_client_place_market_order_with_quantity_builds_expected_params() -> None:
    """
    Test that Spot market orders with quantity build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_market_order(
        symbol="btcusdt",
        side="buy",
        quantity="0.001",
        client_order_id="market_001",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["url"].endswith("/v3/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "MARKET"
    assert request["params"]["quantity"] == "0.001"
    assert "quoteOrderQty" not in request["params"]
    assert request["params"]["newClientOrderId"] == "market_001"
    assert_signed_request(request)


def test_spot_client_place_market_order_with_quote_qty_builds_expected_params() -> None:
    """
    Test that Spot market orders with quote quantity build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_market_order(
        symbol="btcusdt",
        side="buy",
        quote_order_qty="25",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["url"].endswith("/v3/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "MARKET"
    assert request["params"]["quoteOrderQty"] == "25"
    assert "quantity" not in request["params"]
    assert_signed_request(request)


def test_spot_client_place_market_order_requires_one_quantity_type() -> None:
    """
    Test that Spot market orders require one quantity type.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_market_order(
            symbol="BTCUSDT",
            side="BUY",
        )

    assert_no_request(fake_session)


def test_spot_client_place_market_order_rejects_two_quantity_types() -> None:
    """
    Test that Spot market orders reject two quantity types.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_market_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.001",
            quote_order_qty="25",
        )

    assert_no_request(fake_session)


def test_spot_client_place_limit_maker_order_builds_expected_params() -> None:
    """
    Test that Spot limit maker orders build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_limit_maker_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        price="70000.00",
        iceberg_qty="0.0005",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "LIMIT_MAKER"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "70000.00"
    assert request["params"]["icebergQty"] == "0.0005"
    assert_signed_request(request)


def test_spot_client_place_stop_loss_order_builds_expected_params() -> None:
    """
    Test that Spot stop loss orders build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_loss_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        stop_price="49000.00",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "STOP_LOSS"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["stopPrice"] == "49000.00"
    assert_signed_request(request)


def test_spot_client_place_stop_loss_order_with_trailing_delta() -> None:
    """
    Test that Spot stop loss orders accept trailing delta.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_loss_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        trailing_delta=100,
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["type"] == "STOP_LOSS"
    assert request["params"]["trailingDelta"] == 100
    assert "stopPrice" not in request["params"]
    assert_signed_request(request)


def test_spot_client_place_stop_loss_order_requires_trigger() -> None:
    """
    Test that Spot stop loss orders require a trigger.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_stop_loss_order(
            symbol="BTCUSDT",
            side="SELL",
            quantity="0.001",
        )

    assert_no_request(fake_session)


def test_spot_client_place_stop_loss_limit_order_builds_expected_params() -> None:
    """
    Test that Spot stop loss limit orders build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_loss_limit_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        price="48950.00",
        stop_price="49000.00",
        iceberg_qty="0.0005",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "STOP_LOSS_LIMIT"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "48950.00"
    assert request["params"]["stopPrice"] == "49000.00"
    assert request["params"]["icebergQty"] == "0.0005"
    assert_signed_request(request)


def test_spot_client_place_take_profit_order_builds_expected_params() -> None:
    """
    Test that Spot take profit orders build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_take_profit_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        stop_price="70000.00",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TAKE_PROFIT"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["stopPrice"] == "70000.00"
    assert_signed_request(request)


def test_spot_client_place_take_profit_limit_order_builds_expected_params() -> None:
    """
    Test that Spot take profit limit orders build expected parameters.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_take_profit_limit_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        price="70050.00",
        stop_price="70000.00",
        iceberg_qty="0.0005",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TAKE_PROFIT_LIMIT"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "70050.00"
    assert request["params"]["stopPrice"] == "70000.00"
    assert request["params"]["icebergQty"] == "0.0005"
    assert_signed_request(request)


def test_spot_client_place_convenience_order_rejects_invalid_side() -> None:
    """
    Test that Spot convenience orders reject invalid sides.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_limit_order(
            symbol="BTCUSDT",
            side="HOLD",
            quantity="0.001",
            price="50000.00",
        )

    assert_no_request(fake_session)


def test_spot_client_place_oco_order_uses_oco_endpoint() -> None:
    """
    Test that Spot OCO order lists use the OCO endpoint.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderListId": 1}',
            payload={"orderListId": 1},
        )
    )

    order_list = client.place_oco_order(
        params={
            "symbol": "btcusdt",
            "side": "SELL",
            "quantity": "0.001",
            "aboveType": "LIMIT_MAKER",
            "abovePrice": "70000.00",
            "belowType": "STOP_LOSS_LIMIT",
            "belowStopPrice": "60000.00",
            "belowPrice": "59950.00",
            "belowTimeInForce": "GTC",
        }
    )

    request = fake_session.last_request

    assert request is not None
    assert order_list == {"orderListId": 1}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/orderList/oco")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert_signed_request(request)


def test_spot_client_place_oto_order_uses_oto_endpoint() -> None:
    """
    Test that Spot OTO order lists use the OTO endpoint.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderListId": 2}',
            payload={"orderListId": 2},
        )
    )

    order_list = client.place_oto_order(
        params={
            "symbol": "btcusdt",
            "workingSide": "BUY",
            "workingType": "LIMIT",
            "workingQuantity": "0.001",
            "workingPrice": "50000.00",
            "pendingSide": "SELL",
            "pendingType": "LIMIT",
            "pendingQuantity": "0.001",
            "pendingPrice": "70000.00",
        }
    )

    request = fake_session.last_request

    assert request is not None
    assert order_list == {"orderListId": 2}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/orderList/oto")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["workingSide"] == "BUY"
    assert_signed_request(request)


def test_spot_client_place_otoco_order_uses_otoco_endpoint() -> None:
    """
    Test that Spot OTOCO order lists use the OTOCO endpoint.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderListId": 3}',
            payload={"orderListId": 3},
        )
    )

    order_list = client.place_otoco_order(
        params={
            "symbol": "btcusdt",
            "workingSide": "BUY",
            "workingType": "LIMIT",
            "workingQuantity": "0.001",
            "workingPrice": "50000.00",
            "pendingSide": "SELL",
            "pendingQuantity": "0.001",
            "pendingAboveType": "LIMIT_MAKER",
            "pendingAbovePrice": "70000.00",
            "pendingBelowType": "STOP_LOSS_LIMIT",
            "pendingBelowStopPrice": "60000.00",
            "pendingBelowPrice": "59950.00",
            "pendingBelowTimeInForce": "GTC",
        }
    )

    request = fake_session.last_request

    assert request is not None
    assert order_list == {"orderListId": 3}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v3/orderList/otoco")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["workingSide"] == "BUY"
    assert_signed_request(request)


def test_spot_client_place_order_list_raises_when_live_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that live Spot order lists are blocked when trading is disabled.
    """
    monkeypatch.setattr(
        "src.binance.spot_client.ENABLE_TRADING",
        False,
    )

    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(),
        testnet=False,
    )

    with pytest.raises(RuntimeError):
        client.place_oco_order(
            params={
                "symbol": "BTCUSDT",
                "side": "SELL",
                "quantity": "0.001",
            }
        )

    assert_no_request(fake_session)


def test_spot_client_get_order_with_order_id() -> None:
    """
    Test that Spot order lookup works with order ID.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderId": 123}',
            payload={"orderId": 123},
        )
    )

    order = client.get_order(
        symbol="btcusdt",
        order_id=123,
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {"orderId": 123}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["orderId"] == 123
    assert_signed_request(request)


def test_spot_client_get_order_with_client_order_id() -> None:
    """
    Test that Spot order lookup works with client order ID.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"clientOrderId": "abc"}',
            payload={"clientOrderId": "abc"},
        )
    )

    order = client.get_order(
        symbol="btcusdt",
        client_order_id=" abc ",
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {"clientOrderId": "abc"}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["origClientOrderId"] == "abc"
    assert_signed_request(request)


def test_spot_client_get_order_requires_identifier() -> None:
    """
    Test that Spot order lookup requires one identifier.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.get_order(symbol="BTCUSDT")

    assert_no_request(fake_session)


def test_spot_client_get_order_rejects_two_identifiers() -> None:
    """
    Test that Spot order lookup rejects two identifiers.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.get_order(
            symbol="BTCUSDT",
            order_id=123,
            client_order_id="abc",
        )

    assert_no_request(fake_session)


def test_spot_client_get_open_orders_without_symbol() -> None:
    """
    Test that Spot open order lookup works without symbol.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    open_orders = client.get_open_orders()

    request = fake_session.last_request

    assert request is not None
    assert open_orders == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/openOrders")
    assert "symbol" not in request["params"]
    assert_signed_request(request)


def test_spot_client_get_open_orders_with_symbol() -> None:
    """
    Test that Spot open order lookup works with symbol.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    open_orders = client.get_open_orders(symbol="btcusdt")

    request = fake_session.last_request

    assert request is not None
    assert open_orders == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/openOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_spot_client_get_all_orders_uses_expected_params() -> None:
    """
    Test that Spot all-order lookup uses expected parameters.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    orders = client.get_all_orders(
        symbol="btcusdt",
        limit=100,
        order_id=123,
        start_time=1_700_000_000_000,
        end_time=1_700_000_100_000,
    )

    request = fake_session.last_request

    assert request is not None
    assert orders == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/allOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["limit"] == 100
    assert request["params"]["orderId"] == 123
    assert request["params"]["startTime"] == 1_700_000_000_000
    assert request["params"]["endTime"] == 1_700_000_100_000
    assert_signed_request(request)


def test_spot_client_cancel_order_with_order_id() -> None:
    """
    Test that Spot order cancellation works with order ID.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"orderId": 123, "status": "CANCELED"}',
            payload={
                "orderId": 123,
                "status": "CANCELED",
            },
        )
    )

    canceled_order = client.cancel_order(
        symbol="btcusdt",
        order_id=123,
    )

    request = fake_session.last_request

    assert request is not None
    assert canceled_order == {
        "orderId": 123,
        "status": "CANCELED",
    }
    assert request["method"] == "DELETE"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["orderId"] == 123
    assert_signed_request(request)


def test_spot_client_cancel_order_with_client_order_id() -> None:
    """
    Test that Spot order cancellation works with client order ID.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"clientOrderId": "abc", "status": "CANCELED"}',
            payload={
                "clientOrderId": "abc",
                "status": "CANCELED",
            },
        )
    )

    canceled_order = client.cancel_order(
        symbol="btcusdt",
        client_order_id=" abc ",
    )

    request = fake_session.last_request

    assert request is not None
    assert canceled_order == {
        "clientOrderId": "abc",
        "status": "CANCELED",
    }
    assert request["method"] == "DELETE"
    assert request["url"].endswith("/v3/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["origClientOrderId"] == "abc"
    assert_signed_request(request)


def test_spot_client_cancel_order_requires_identifier() -> None:
    """
    Test that Spot order cancellation requires one identifier.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.cancel_order(symbol="BTCUSDT")

    assert_no_request(fake_session)


def test_spot_client_cancel_order_rejects_two_identifiers() -> None:
    """
    Test that Spot order cancellation rejects two identifiers.
    """
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.cancel_order(
            symbol="BTCUSDT",
            order_id=123,
            client_order_id="abc",
        )

    assert_no_request(fake_session)


def test_spot_client_cancel_all_open_orders_uses_expected_endpoint() -> None:
    """
    Test that Spot open-order cancellation uses the expected endpoint.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    canceled_orders = client.cancel_all_open_orders(symbol="btcusdt")

    request = fake_session.last_request

    assert request is not None
    assert canceled_orders == []
    assert request["method"] == "DELETE"
    assert request["url"].endswith("/v3/openOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_spot_client_get_my_trades_uses_expected_params() -> None:
    """
    Test that Spot account trade lookup uses expected parameters.
    """
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    trades = client.get_my_trades(
        symbol="btcusdt",
        limit=100,
        from_id=99,
        start_time=1_700_000_000_000,
        end_time=1_700_000_100_000,
    )

    request = fake_session.last_request

    assert request is not None
    assert trades == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/myTrades")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["limit"] == 100
    assert request["params"]["fromId"] == 99
    assert request["params"]["startTime"] == 1_700_000_000_000
    assert request["params"]["endTime"] == 1_700_000_100_000
    assert_signed_request(request)
