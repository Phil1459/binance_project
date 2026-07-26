from typing import Any


def normalize_symbol(symbol: str) -> str:
    normalized_symbol = symbol.strip().upper()

    if normalized_symbol == "":
        raise ValueError("symbol must not be empty")

    return normalized_symbol


def normalize_client_order_id(client_order_id: str) -> str:
    normalized_client_order_id = client_order_id.strip()

    if normalized_client_order_id == "":
        raise ValueError("client_order_id must not be empty")

    return normalized_client_order_id


def normalize_order_side(side: str) -> str:
    normalized_side = side.strip().upper()

    if normalized_side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    return normalized_side


def normalize_order_params_symbol(
    params: dict[str, Any],
) -> dict[str, Any]:
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
    if (order_id is None) == (client_order_id is None):
        raise ValueError("Exactly one of order_id or client_order_id is required")
