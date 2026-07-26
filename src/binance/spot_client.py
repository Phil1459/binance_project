import logging
from typing import Any

from config.settings import (
    BINANCE_API_KEY,
    BINANCE_API_KEY_TESTNET,
    BINANCE_API_SECRET,
    BINANCE_API_SECRET_TESTNET,
    BINANCE_TESTNET,
    ENABLE_TRADING,
)
from src.binance.base_client import BaseClientRest
from src.binance.endpoints import get_base_url_spot_rest
from src.binance.normalization import (
    normalize_client_order_id,
    normalize_order_params_symbol,
    normalize_order_side,
    normalize_symbol,
    validate_exactly_one_order_identifier,
)

logger = logging.getLogger(__name__)


class SpotClient(BaseClientRest):
    def __init__(
        self,
        testnet: bool | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        if testnet is None:
            testnet = BINANCE_TESTNET

        if api_key is None:
            if testnet:
                api_key = BINANCE_API_KEY_TESTNET
            else:
                api_key = BINANCE_API_KEY

        if api_secret is None:
            if testnet:
                api_secret = BINANCE_API_SECRET_TESTNET
            else:
                api_secret = BINANCE_API_SECRET

        base_url = get_base_url_spot_rest(testnet=testnet)

        super().__init__(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            api_key=api_key,
            api_secret=api_secret,
        )

        self.testnet = testnet

        logger.info(
            "Initialized SpotClient testnet=%s base_url=%s",
            self.testnet,
            self.base_url,
        )

    def _add_new_client_order_id(
        self,
        params: dict[str, Any],
        client_order_id: str | None,
    ) -> dict[str, Any]:
        if client_order_id is not None:
            params["newClientOrderId"] = normalize_client_order_id(client_order_id)

        return params

    def _add_iceberg_qty(
        self,
        params: dict[str, Any],
        iceberg_qty: str | None,
    ) -> dict[str, Any]:
        if iceberg_qty is not None:
            params["icebergQty"] = iceberg_qty

        return params

    def _add_stop_trigger(
        self,
        params: dict[str, Any],
        stop_price: str | None,
        trailing_delta: int | None,
    ) -> dict[str, Any]:
        if stop_price is None and trailing_delta is None:
            raise ValueError("Either stop_price or trailing_delta is required")

        if stop_price is not None:
            params["stopPrice"] = stop_price

        if trailing_delta is not None:
            params["trailingDelta"] = trailing_delta

        return params

    def _validate_exactly_one_market_quantity(
        self,
        quantity: str | None,
        quote_order_qty: str | None,
    ) -> None:
        if (quantity is None) == (quote_order_qty is None):
            raise ValueError("Exactly one of quantity or quote_order_qty is required")

    def ping(self) -> bool:
        self._request(
            method="GET",
            path="/v3/ping",
        )

        logger.debug("Binance Spot ping successful")

        return True

    def get_server_time(self) -> int:
        data = self._request(
            method="GET",
            path="/v3/time",
        )

        server_time = data["serverTime"]

        if not isinstance(server_time, int):
            raise TypeError("Binance Spot serverTime response value is not an integer")

        logger.debug(
            "Received Binance Spot server time server_time=%s",
            server_time,
        )

        return server_time

    def get_account_info(self) -> dict[str, Any]:
        account_info = self._signed_request(
            method="GET",
            path="/v3/account",
        )

        logger.debug("Received Binance Spot account info")

        return account_info

    def place_order(
        self,
        params: dict[str, Any],
        test: bool = True,
    ) -> dict[str, Any]:
        if not test and not self.testnet and not ENABLE_TRADING:
            raise RuntimeError(
                "Real trading is disabled. "
                "Set ENABLE_TRADING=true to allow live orders."
            )

        order_params = normalize_order_params_symbol(params)

        path = "/v3/order/test" if test else "/v3/order"

        order = self._signed_request(
            method="POST",
            path=path,
            params=order_params,
        )

        logger.info(
            "Placed Binance Spot order test=%s symbol=%s side=%s type=%s",
            test,
            order_params.get("symbol"),
            order_params.get("side"),
            order_params.get("type"),
        )

        return order

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        time_in_force: str = "GTC",
        iceberg_qty: str | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "LIMIT",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
        }

        params = self._add_iceberg_qty(
            params=params,
            iceberg_qty=iceberg_qty,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | None = None,
        quote_order_qty: str | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        self._validate_exactly_one_market_quantity(
            quantity=quantity,
            quote_order_qty=quote_order_qty,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "MARKET",
        }

        if quantity is not None:
            params["quantity"] = quantity

        if quote_order_qty is not None:
            params["quoteOrderQty"] = quote_order_qty

        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_limit_maker_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        iceberg_qty: str | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "LIMIT_MAKER",
            "quantity": quantity,
            "price": price,
        }

        params = self._add_iceberg_qty(
            params=params,
            iceberg_qty=iceberg_qty,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        stop_price: str | None = None,
        trailing_delta: int | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "STOP_LOSS",
            "quantity": quantity,
        }

        params = self._add_stop_trigger(
            params=params,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_stop_loss_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        stop_price: str | None = None,
        trailing_delta: int | None = None,
        time_in_force: str = "GTC",
        iceberg_qty: str | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "STOP_LOSS_LIMIT",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
        }

        params = self._add_stop_trigger(
            params=params,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
        )
        params = self._add_iceberg_qty(
            params=params,
            iceberg_qty=iceberg_qty,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        stop_price: str | None = None,
        trailing_delta: int | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "TAKE_PROFIT",
            "quantity": quantity,
        }

        params = self._add_stop_trigger(
            params=params,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_take_profit_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        stop_price: str | None = None,
        trailing_delta: int | None = None,
        time_in_force: str = "GTC",
        iceberg_qty: str | None = None,
        client_order_id: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": normalize_order_side(side),
            "type": "TAKE_PROFIT_LIMIT",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
        }

        params = self._add_stop_trigger(
            params=params,
            stop_price=stop_price,
            trailing_delta=trailing_delta,
        )
        params = self._add_iceberg_qty(
            params=params,
            iceberg_qty=iceberg_qty,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_oco_order(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.testnet and not ENABLE_TRADING:
            raise RuntimeError(
                "Real trading is disabled. "
                "Set ENABLE_TRADING=true to allow live order lists."
            )

        order_params = normalize_order_params_symbol(params)

        order_list = self._signed_request(
            method="POST",
            path="/v3/orderList/oco",
            params=order_params,
        )

        logger.info(
            "Placed Binance Spot OCO order list symbol=%s side=%s",
            order_params.get("symbol"),
            order_params.get("side"),
        )

        return order_list

    def place_oto_order(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.testnet and not ENABLE_TRADING:
            raise RuntimeError(
                "Real trading is disabled. "
                "Set ENABLE_TRADING=true to allow live order lists."
            )

        order_params = normalize_order_params_symbol(params)

        order_list = self._signed_request(
            method="POST",
            path="/v3/orderList/oto",
            params=order_params,
        )

        logger.info(
            "Placed Binance Spot OTO order list symbol=%s working_side=%s",
            order_params.get("symbol"),
            order_params.get("workingSide"),
        )

        return order_list

    def place_otoco_order(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.testnet and not ENABLE_TRADING:
            raise RuntimeError(
                "Real trading is disabled. "
                "Set ENABLE_TRADING=true to allow live order lists."
            )

        order_params = normalize_order_params_symbol(params)

        order_list = self._signed_request(
            method="POST",
            path="/v3/orderList/otoco",
            params=order_params,
        )

        logger.info(
            "Placed Binance Spot OTOCO order list symbol=%s working_side=%s",
            order_params.get("symbol"),
            order_params.get("workingSide"),
        )

        return order_list

    def get_order(
        self,
        symbol: str,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        validate_exactly_one_order_identifier(
            order_id=order_id,
            client_order_id=client_order_id,
        )

        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
        }

        if order_id is not None:
            params["orderId"] = order_id

        if client_order_id is not None:
            params["origClientOrderId"] = normalize_client_order_id(client_order_id)

        return self._signed_request(
            method="GET",
            path="/v3/order",
            params=params,
        )

    def get_open_orders(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}

        if symbol is not None:
            params["symbol"] = normalize_symbol(symbol)

        return self._signed_request(
            method="GET",
            path="/v3/openOrders",
            params=params,
        )

    def get_all_orders(
        self,
        symbol: str,
        limit: int = 500,
        order_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
            "limit": limit,
        }

        if order_id is not None:
            params["orderId"] = order_id

        if start_time is not None:
            params["startTime"] = start_time

        if end_time is not None:
            params["endTime"] = end_time

        return self._signed_request(
            method="GET",
            path="/v3/allOrders",
            params=params,
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        validate_exactly_one_order_identifier(
            order_id=order_id,
            client_order_id=client_order_id,
        )

        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
        }

        if order_id is not None:
            params["orderId"] = order_id

        if client_order_id is not None:
            params["origClientOrderId"] = normalize_client_order_id(client_order_id)

        canceled_order = self._signed_request(
            method="DELETE",
            path="/v3/order",
            params=params,
        )

        logger.info(
            "Canceled Binance Spot order symbol=%s order_id=%s client_order_id=%s",
            params["symbol"],
            order_id,
            client_order_id,
        )

        return canceled_order

    def cancel_all_open_orders(
        self,
        symbol: str,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
        }

        canceled_orders = self._signed_request(
            method="DELETE",
            path="/v3/openOrders",
            params=params,
        )

        logger.info(
            "Canceled all Binance Spot open orders symbol=%s",
            params["symbol"],
        )

        return canceled_orders

    def get_my_trades(
        self,
        symbol: str,
        limit: int = 500,
        from_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
            "limit": limit,
        }

        if from_id is not None:
            params["fromId"] = from_id

        if start_time is not None:
            params["startTime"] = start_time

        if end_time is not None:
            params["endTime"] = end_time

        return self._signed_request(
            method="GET",
            path="/v3/myTrades",
            params=params,
        )
