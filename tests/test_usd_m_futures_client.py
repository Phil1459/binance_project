from typing import Any

import pytest
from src.binance.usd_m_futures_client import UsdMFuturesClient


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

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        raise RuntimeError("Fake HTTP error")


# Minimal fake requests session.
class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
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
) -> tuple[UsdMFuturesClient, FakeSession]:
    client = UsdMFuturesClient(
        testnet=testnet,
        api_key="fake_key",
        api_secret="fake_secret",
    )

    fake_session = FakeSession(response=response)
    client.session = fake_session

    return client, fake_session


def assert_signed_request(request: dict[str, Any]) -> None:
    assert request["headers"] == {
        "X-MBX-APIKEY": "fake_key",
    }

    assert request["params"]["recvWindow"] == 5000
    assert "timestamp" in request["params"]
    assert "signature" in request["params"]


def assert_no_request(fake_session: FakeSession) -> None:
    assert fake_session.last_request is None


def test_usd_m_futures_client_ping_returns_true() -> None:
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
    assert fake_session.last_request["url"].endswith("/v1/ping")
    assert fake_session.last_request["params"] is None


def test_usd_m_futures_client_get_server_time_returns_integer() -> None:
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
    assert fake_session.last_request["url"].endswith("/v1/time")
    assert fake_session.last_request["params"] is None


def test_usd_m_futures_client_get_server_time_raises_for_non_integer() -> None:
    client, _ = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"serverTime": "1234567890"}',
            payload={"serverTime": "1234567890"},
        )
    )

    with pytest.raises(TypeError):
        client.get_server_time()


def test_usd_m_futures_client_get_account_info_uses_signed_request() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"assets": []}',
            payload={"assets": []},
        )
    )

    account_info = client.get_account_info()

    request = fake_session.last_request

    assert request is not None
    assert account_info == {"assets": []}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/account")
    assert_signed_request(request)


def test_usd_m_futures_client_get_account_balance_uses_expected_endpoint() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    balance = client.get_account_balance()

    request = fake_session.last_request

    assert request is not None
    assert balance == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/balance")
    assert_signed_request(request)


def test_usd_m_futures_client_get_position_risk_without_symbol() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    positions = client.get_position_risk()

    request = fake_session.last_request

    assert request is not None
    assert positions == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/positionRisk")
    assert "symbol" not in request["params"]
    assert_signed_request(request)


def test_usd_m_futures_client_get_position_risk_with_symbol() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text="[]",
            payload=[],
        )
    )

    positions = client.get_position_risk(symbol="btcusdt")

    request = fake_session.last_request

    assert request is not None
    assert positions == []
    assert request["method"] == "GET"
    assert request["url"].endswith("/v3/positionRisk")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_usd_m_futures_client_get_position_mode_uses_expected_endpoint() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"dualSidePosition": false}',
            payload={"dualSidePosition": False},
        )
    )

    position_mode = client.get_position_mode()

    request = fake_session.last_request

    assert request is not None
    assert position_mode == {"dualSidePosition": False}
    assert request["method"] == "GET"
    assert request["url"].endswith("/v1/positionSide/dual")
    assert_signed_request(request)


def test_usd_m_futures_client_change_leverage_uses_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"symbol": "BTCUSDT", "leverage": 10}',
            payload={"symbol": "BTCUSDT", "leverage": 10},
        )
    )

    result = client.change_leverage(
        symbol="btcusdt",
        leverage=10,
    )

    request = fake_session.last_request

    assert request is not None
    assert result == {"symbol": "BTCUSDT", "leverage": 10}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v1/leverage")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["leverage"] == 10
    assert_signed_request(request)


def test_usd_m_futures_client_change_margin_type_uses_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"code": 200, "msg": "success"}',
            payload={"code": 200, "msg": "success"},
        )
    )

    result = client.change_margin_type(
        symbol="btcusdt",
        margin_type=" isolated ",
    )

    request = fake_session.last_request

    assert request is not None
    assert result == {"code": 200, "msg": "success"}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v1/marginType")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["marginType"] == "ISOLATED"
    assert_signed_request(request)


def test_usd_m_futures_client_change_margin_type_rejects_invalid_value() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.change_margin_type(
            symbol="BTCUSDT",
            margin_type="INVALID",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_place_order_uses_test_order_endpoint() -> None:
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
            "side": "buy",
            "type": "limit",
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
    assert request["url"].endswith("/v1/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "LIMIT"
    assert_signed_request(request)


def test_usd_m_futures_client_place_testnet_order_allowed_when_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.binance.usd_m_futures_client.ENABLE_TRADING",
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
            "quantity": "0.001",
        },
        test=False,
    )

    request = fake_session.last_request

    assert request is not None
    assert order == {"orderId": 123}
    assert request["method"] == "POST"
    assert request["url"].endswith("/v1/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_usd_m_futures_client_place_live_order_raises_when_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.binance.usd_m_futures_client.ENABLE_TRADING",
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
                "quantity": "0.001",
            },
            test=False,
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_place_order_requires_side() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_order(
            params={
                "symbol": "BTCUSDT",
                "type": "MARKET",
                "quantity": "0.001",
            }
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_place_order_requires_type() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_order(
            params={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": "0.001",
            }
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_place_limit_order_builds_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_limit_order(
        symbol="btcusdt",
        side="buy",
        quantity="0.001",
        price="50000.00",
        position_side="long",
        reduce_only=True,
        client_order_id=" limit_001 ",
        new_order_resp_type="result",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["url"].endswith("/v1/order/test")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "BUY"
    assert request["params"]["type"] == "LIMIT"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "50000.00"
    assert request["params"]["positionSide"] == "LONG"
    assert request["params"]["reduceOnly"] == "true"
    assert request["params"]["newClientOrderId"] == "limit_001"
    assert request["params"]["newOrderRespType"] == "RESULT"
    assert_signed_request(request)


def test_usd_m_futures_client_place_market_order_builds_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_market_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        position_side="short",
        reduce_only=False,
        client_order_id="market_001",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "MARKET"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["positionSide"] == "SHORT"
    assert request["params"]["reduceOnly"] == "false"
    assert request["params"]["newClientOrderId"] == "market_001"
    assert_signed_request(request)


def test_usd_m_futures_client_place_stop_order_builds_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        price="48950.00",
        stop_price="49000.00",
        working_type="mark_price",
        price_protect=True,
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "STOP"
    assert request["params"]["timeInForce"] == "GTC"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "48950.00"
    assert request["params"]["stopPrice"] == "49000.00"
    assert request["params"]["workingType"] == "MARK_PRICE"
    assert request["params"]["priceProtect"] == "true"
    assert_signed_request(request)


def test_usd_m_futures_client_place_stop_market_order_with_quantity() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_market_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        stop_price="49000.00",
        working_type="contract_price",
        price_protect=False,
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "STOP_MARKET"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["stopPrice"] == "49000.00"
    assert request["params"]["workingType"] == "CONTRACT_PRICE"
    assert request["params"]["priceProtect"] == "false"
    assert_signed_request(request)


def test_usd_m_futures_client_place_stop_market_order_with_close_position() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_stop_market_order(
        symbol="btcusdt",
        side="sell",
        stop_price="49000.00",
        close_position=True,
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "STOP_MARKET"
    assert request["params"]["stopPrice"] == "49000.00"
    assert request["params"]["closePosition"] == "true"
    assert "quantity" not in request["params"]
    assert_signed_request(request)


def test_usd_m_futures_client_place_stop_market_order_requires_quantity_or_close() -> (
    None
):
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_stop_market_order(
            symbol="BTCUSDT",
            side="SELL",
            stop_price="49000.00",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_place_take_profit_order_builds_expected_params() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_take_profit_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        price="70050.00",
        stop_price="70000.00",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TAKE_PROFIT"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["price"] == "70050.00"
    assert request["params"]["stopPrice"] == "70000.00"
    assert_signed_request(request)


def test_usd_m_futures_client_place_take_profit_market_order_with_quantity() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_take_profit_market_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        stop_price="70000.00",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TAKE_PROFIT_MARKET"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["stopPrice"] == "70000.00"
    assert_signed_request(request)


def test_usd_m_futures_client_place_take_profit_market_order_with_close_position() -> (
    None
):
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_take_profit_market_order(
        symbol="btcusdt",
        side="sell",
        stop_price="70000.00",
        close_position=True,
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TAKE_PROFIT_MARKET"
    assert request["params"]["stopPrice"] == "70000.00"
    assert request["params"]["closePosition"] == "true"
    assert "quantity" not in request["params"]
    assert_signed_request(request)


def test_usd_m_futures_client_place_trailing_stop_market_order() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    client.place_trailing_stop_market_order(
        symbol="btcusdt",
        side="sell",
        quantity="0.001",
        callback_rate="0.5",
        activation_price="70000.00",
        working_type="mark_price",
    )

    request = fake_session.last_request

    assert request is not None
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["side"] == "SELL"
    assert request["params"]["type"] == "TRAILING_STOP_MARKET"
    assert request["params"]["quantity"] == "0.001"
    assert request["params"]["callbackRate"] == "0.5"
    assert request["params"]["activationPrice"] == "70000.00"
    assert request["params"]["workingType"] == "MARK_PRICE"
    assert_signed_request(request)


def test_usd_m_futures_client_rejects_invalid_position_side() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_limit_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.001",
            price="50000.00",
            position_side="INVALID",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_rejects_invalid_working_type() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_stop_order(
            symbol="BTCUSDT",
            side="SELL",
            quantity="0.001",
            price="48950.00",
            stop_price="49000.00",
            working_type="INVALID",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_rejects_invalid_new_order_resp_type() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.place_limit_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.001",
            price="50000.00",
            new_order_resp_type="FULL",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_get_order_with_order_id() -> None:
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
    assert request["url"].endswith("/v1/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["orderId"] == 123
    assert_signed_request(request)


def test_usd_m_futures_client_get_order_with_client_order_id() -> None:
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
    assert request["url"].endswith("/v1/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["origClientOrderId"] == "abc"
    assert_signed_request(request)


def test_usd_m_futures_client_get_order_requires_identifier() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.get_order(symbol="BTCUSDT")

    assert_no_request(fake_session)


def test_usd_m_futures_client_get_order_rejects_two_identifiers() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.get_order(
            symbol="BTCUSDT",
            order_id=123,
            client_order_id="abc",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_get_open_orders_without_symbol() -> None:
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
    assert request["url"].endswith("/v1/openOrders")
    assert "symbol" not in request["params"]
    assert_signed_request(request)


def test_usd_m_futures_client_get_open_orders_with_symbol() -> None:
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
    assert request["url"].endswith("/v1/openOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_usd_m_futures_client_get_all_orders_uses_expected_params() -> None:
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
    assert request["url"].endswith("/v1/allOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["limit"] == 100
    assert request["params"]["orderId"] == 123
    assert request["params"]["startTime"] == 1_700_000_000_000
    assert request["params"]["endTime"] == 1_700_000_100_000
    assert_signed_request(request)


def test_usd_m_futures_client_cancel_order_with_order_id() -> None:
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
    assert request["url"].endswith("/v1/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["orderId"] == 123
    assert_signed_request(request)


def test_usd_m_futures_client_cancel_order_with_client_order_id() -> None:
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
    assert request["url"].endswith("/v1/order")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["origClientOrderId"] == "abc"
    assert_signed_request(request)


def test_usd_m_futures_client_cancel_order_requires_identifier() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.cancel_order(symbol="BTCUSDT")

    assert_no_request(fake_session)


def test_usd_m_futures_client_cancel_order_rejects_two_identifiers() -> None:
    client, fake_session = create_client_with_fake_session(response=FakeResponse())

    with pytest.raises(ValueError):
        client.cancel_order(
            symbol="BTCUSDT",
            order_id=123,
            client_order_id="abc",
        )

    assert_no_request(fake_session)


def test_usd_m_futures_client_cancel_all_open_orders_uses_expected_endpoint() -> None:
    client, fake_session = create_client_with_fake_session(
        response=FakeResponse(
            status_code=200,
            text='{"code": 200, "msg": "success"}',
            payload={"code": 200, "msg": "success"},
        )
    )

    canceled_orders = client.cancel_all_open_orders(symbol="btcusdt")

    request = fake_session.last_request

    assert request is not None
    assert canceled_orders == {"code": 200, "msg": "success"}
    assert request["method"] == "DELETE"
    assert request["url"].endswith("/v1/allOpenOrders")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert_signed_request(request)


def test_usd_m_futures_client_get_my_trades_uses_expected_params() -> None:
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
    assert request["url"].endswith("/v1/userTrades")
    assert request["params"]["symbol"] == "BTCUSDT"
    assert request["params"]["limit"] == 100
    assert request["params"]["fromId"] == 99
    assert request["params"]["startTime"] == 1_700_000_000_000
    assert request["params"]["endTime"] == 1_700_000_100_000
    assert_signed_request(request)
