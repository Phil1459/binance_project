import pytest
from src.binance.normalization import (
    normalize_client_order_id,
    normalize_order_params_symbol,
    normalize_order_side,
    normalize_symbol,
    validate_exactly_one_order_identifier,
)


# Symbol normalization.
def test_normalize_symbol_uppercases_symbol() -> None:
    symbol = normalize_symbol("btcusdt")

    assert symbol == "BTCUSDT"


def test_normalize_symbol_strips_whitespace() -> None:
    symbol = normalize_symbol("  ethusdt  ")

    assert symbol == "ETHUSDT"


def test_normalize_symbol_raises_for_empty_string() -> None:
    with pytest.raises(ValueError):
        normalize_symbol("")


def test_normalize_symbol_raises_for_whitespace_only_string() -> None:
    with pytest.raises(ValueError):
        normalize_symbol("   ")


# Client order id normalization.
def test_normalize_client_order_id_strips_whitespace() -> None:
    client_order_id = normalize_client_order_id("  order_123  ")

    assert client_order_id == "order_123"


def test_normalize_client_order_id_raises_for_empty_string() -> None:
    with pytest.raises(ValueError):
        normalize_client_order_id("")


def test_normalize_client_order_id_raises_for_whitespace_only_string() -> None:
    with pytest.raises(ValueError):
        normalize_client_order_id("   ")


# Order side normalization.
def test_normalize_order_side_uppercases_side() -> None:
    side = normalize_order_side("buy")

    assert side == "BUY"


def test_normalize_order_side_strips_whitespace() -> None:
    side = normalize_order_side("  sell  ")

    assert side == "SELL"


def test_normalize_order_side_raises_for_invalid_side() -> None:
    with pytest.raises(ValueError):
        normalize_order_side("HOLD")


def test_normalize_order_side_raises_for_empty_string() -> None:
    with pytest.raises(ValueError):
        normalize_order_side("")


# Order params normalization.
def test_normalize_order_params_symbol_uppercases_symbol() -> None:
    params = {
        "symbol": "btcusdt",
        "side": "BUY",
        "type": "MARKET",
    }

    normalized_params = normalize_order_params_symbol(params)

    assert normalized_params["symbol"] == "BTCUSDT"
    assert normalized_params["side"] == "BUY"
    assert normalized_params["type"] == "MARKET"


def test_normalize_order_params_symbol_does_not_mutate_original_params() -> None:
    params = {
        "symbol": "btcusdt",
        "side": "BUY",
    }

    normalized_params = normalize_order_params_symbol(params)

    assert params["symbol"] == "btcusdt"
    assert normalized_params["symbol"] == "BTCUSDT"


def test_normalize_order_params_symbol_raises_when_symbol_is_missing() -> None:
    params = {
        "side": "BUY",
        "type": "MARKET",
    }

    with pytest.raises(ValueError):
        normalize_order_params_symbol(params)


def test_normalize_order_params_symbol_raises_when_symbol_is_not_string() -> None:
    params = {
        "symbol": 123,
        "side": "BUY",
    }

    with pytest.raises(TypeError):
        normalize_order_params_symbol(params)


def test_normalize_order_params_symbol_raises_when_symbol_is_empty() -> None:
    params = {
        "symbol": "",
        "side": "BUY",
    }

    with pytest.raises(ValueError):
        normalize_order_params_symbol(params)


def test_normalize_order_params_symbol_raises_when_symbol_is_whitespace_only() -> None:
    params = {
        "symbol": "   ",
        "side": "BUY",
    }

    with pytest.raises(ValueError):
        normalize_order_params_symbol(params)


# Order identifier validation.
def test_validate_exactly_one_order_identifier_accepts_order_id() -> None:
    validate_exactly_one_order_identifier(
        order_id=123,
        client_order_id=None,
    )


def test_validate_exactly_one_order_identifier_accepts_client_order_id() -> None:
    validate_exactly_one_order_identifier(
        order_id=None,
        client_order_id="order_123",
    )


def test_validate_exactly_one_order_identifier_raises_when_both_are_missing() -> None:
    with pytest.raises(ValueError):
        validate_exactly_one_order_identifier(
            order_id=None,
            client_order_id=None,
        )


def test_validate_exactly_one_order_identifier_raises_when_both_are_set() -> None:
    with pytest.raises(ValueError):
        validate_exactly_one_order_identifier(
            order_id=123,
            client_order_id="order_123",
        )
