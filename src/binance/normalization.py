# Binance parameter normalization helpers.
"""
Provide Binance request parameter normalization.

This module contains helpers for normalizing symbols, order sides, client order
IDs, and order identifier validation.
"""

from typing import Any


def normalize_symbol(symbol: str) -> str:
    """
    Return a stripped uppercase Binance symbol.

    Parameters:
        symbol (str): Trading pair symbol.

    Returns:
        str: Normalized trading pair symbol.
    """
    normalized_symbol = symbol.strip().upper()

    if normalized_symbol == "":
        raise ValueError("symbol must not be empty")

    return normalized_symbol


def normalize_client_order_id(client_order_id: str) -> str:
    """
    Return a stripped Binance client order ID.

    Parameters:
        client_order_id (str): Client-defined order ID.

    Returns:
        str: Normalized client order ID.
    """
    normalized_client_order_id = client_order_id.strip()

    if normalized_client_order_id == "":
        raise ValueError("client_order_id must not be empty")

    return normalized_client_order_id


def normalize_order_side(side: str) -> str:
    """
    Return a normalized Binance order side.

    Parameters:
        side (str): Order side, BUY or SELL.

    Returns:
        str: Normalized order side.
    """
    normalized_side = side.strip().upper()

    if normalized_side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    return normalized_side


def normalize_order_params_symbol(
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Return order parameters with a normalized symbol.

    Parameters:
        params (dict[str, Any]): Binance order parameters.

    Returns:
        dict[str, Any]: Order parameters with normalized symbol.
    """
    normalized_params = dict(params)

    symbol = normalized_params.get("symbol")

    if symbol is None:
        raise ValueError("symbol is required")

    if not isinstance(symbol, str):
        raise TypeError("symbol must be a string")

    normalized_params["symbol"] = normalize_symbol(symbol)

    return normalized_params


def validate_exactly_one_order_identifier(
    order_id: int | None,
    client_order_id: str | None,
) -> None:
    """
    Validate that exactly one order identifier is provided.

    Parameters:
        order_id (int | None): Binance-generated order ID.
        client_order_id (str | None): Client-defined order ID.
    """
    if (order_id is None) == (client_order_id is None):
        raise ValueError("Exactly one of order_id or client_order_id is required")
