# Binance USD-M Futures REST client implementation.
"""
Provide Binance USD-M Futures REST client functionality.

This module contains public, account, position, order, cancellation, and trade
methods for Binance USD-M Futures.
"""

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
from src.binance.endpoints import get_base_url_usd_m_futures_rest
from src.binance.normalization import (
    normalize_client_order_id,
    normalize_order_params_symbol,
    normalize_order_side,
    normalize_symbol,
    validate_exactly_one_order_identifier,
)

logger = logging.getLogger(__name__)


class UsdMFuturesClient(BaseClientRest):
    """
    A client for Binance USD-M Futures REST endpoints.

    Attributes:
        testnet (bool): Whether the client uses the Binance Futures testnet.
        base_url (str): Binance USD-M Futures REST base URL.
        timeout_seconds (int): HTTP request timeout in seconds.
        api_key (str | None): Binance API key for signed requests.
        api_secret (str | None): Binance API secret for signed requests.
        session (requests.Session): HTTP session used for REST requests.
    """

    def __init__(
        self,
        testnet: bool | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        """
        Initialize a Binance USD-M Futures REST client.

        Parameters:
            testnet (bool | None): Whether to use the Binance Futures testnet.
            api_key (str | None): Binance API key for signed requests.
            api_secret (str | None): Binance API secret for signed requests.
            timeout_seconds (int): HTTP request timeout in seconds.
        """
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

        base_url = get_base_url_usd_m_futures_rest(testnet=testnet)

        super().__init__(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            api_key=api_key,
            api_secret=api_secret,
        )

        self.testnet = testnet

        logger.info(
            "Initialized UsdMFuturesClient testnet=%s base_url=%s",
            self.testnet,
            self.base_url,
        )

    def _add_new_client_order_id(
        self,
        params: dict[str, Any],
        client_order_id: str | None,
    ) -> dict[str, Any]:
        """
        Add a Binance client order ID if provided.

        Parameters:
            params (dict[str, Any]): Binance order parameters.
            client_order_id (str | None): Client-defined order ID.

        Returns:
            dict[str, Any]: Order parameters with optional client order ID.
        """
        if client_order_id is not None:
            params["newClientOrderId"] = normalize_client_order_id(client_order_id)

        return params

    def _add_bool_param(
        self,
        params: dict[str, Any],
        name: str,
        value: bool | None,
    ) -> dict[str, Any]:
        """
        Add a Binance-compatible boolean parameter if provided.

        Parameters:
            params (dict[str, Any]): Binance request parameters.
            name (str): Binance parameter name.
            value (bool | None): Optional boolean value.

        Returns:
            dict[str, Any]: Parameters with optional boolean field.
        """
        if value is not None:
            params[name] = "true" if value else "false"

        return params

    def _add_optional_param(
        self,
        params: dict[str, Any],
        name: str,
        value: Any,
    ) -> dict[str, Any]:
        """
        Add an optional Binance parameter if provided.

        Parameters:
            params (dict[str, Any]): Binance request parameters.
            name (str): Binance parameter name.
            value (Any): Optional parameter value.

        Returns:
            dict[str, Any]: Parameters with optional field.
        """
        if value is not None:
            params[name] = value

        return params

    def _add_position_side(
        self,
        params: dict[str, Any],
        position_side: str | None,
    ) -> dict[str, Any]:
        """
        Add a normalized Futures position side if provided.

        Parameters:
            params (dict[str, Any]): Binance order parameters.
            position_side (str | None): Position side, BOTH, LONG, or SHORT.

        Returns:
            dict[str, Any]: Order parameters with optional position side.
        """
        if position_side is None:
            return params

        normalized_position_side = position_side.strip().upper()

        if normalized_position_side not in {"BOTH", "LONG", "SHORT"}:
            raise ValueError("position_side must be BOTH, LONG or SHORT")

        params["positionSide"] = normalized_position_side

        return params

    def _add_working_type(
        self,
        params: dict[str, Any],
        working_type: str | None,
    ) -> dict[str, Any]:
        """
        Add a normalized Futures working type if provided.

        Parameters:
            params (dict[str, Any]): Binance order parameters.
            working_type (str | None): Trigger price type.

        Returns:
            dict[str, Any]: Order parameters with optional working type.
        """
        if working_type is None:
            return params

        normalized_working_type = working_type.strip().upper()

        if normalized_working_type not in {"MARK_PRICE", "CONTRACT_PRICE"}:
            raise ValueError("working_type must be MARK_PRICE or CONTRACT_PRICE")

        params["workingType"] = normalized_working_type

        return params

    def _add_new_order_resp_type(
        self,
        params: dict[str, Any],
        new_order_resp_type: str | None,
    ) -> dict[str, Any]:
        """
        Add a normalized order response type if provided.

        Parameters:
            params (dict[str, Any]): Binance order parameters.
            new_order_resp_type (str | None): Response type, ACK or RESULT.

        Returns:
            dict[str, Any]: Order parameters with optional response type.
        """
        if new_order_resp_type is None:
            return params

        normalized_resp_type = new_order_resp_type.strip().upper()

        if normalized_resp_type not in {"ACK", "RESULT"}:
            raise ValueError("new_order_resp_type must be ACK or RESULT")

        params["newOrderRespType"] = normalized_resp_type

        return params

    def _add_common_order_params(
        self,
        params: dict[str, Any],
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        price_protect: bool | None = None,
        new_order_resp_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Add shared USD-M Futures order parameters.

        Parameters:
            params (dict[str, Any]): Binance order parameters.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            price_protect (bool | None): Optional price protection flag.
            new_order_resp_type (str | None): Optional order response type.

        Returns:
            dict[str, Any]: Order parameters with optional shared fields.
        """
        params = self._add_position_side(
            params=params,
            position_side=position_side,
        )
        params = self._add_bool_param(
            params=params,
            name="reduceOnly",
            value=reduce_only,
        )
        params = self._add_new_client_order_id(
            params=params,
            client_order_id=client_order_id,
        )
        params = self._add_working_type(
            params=params,
            working_type=working_type,
        )
        params = self._add_bool_param(
            params=params,
            name="priceProtect",
            value=price_protect,
        )
        params = self._add_new_order_resp_type(
            params=params,
            new_order_resp_type=new_order_resp_type,
        )

        return params

    def _normalize_order_params(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return normalized USD-M Futures order parameters.

        Parameters:
            params (dict[str, Any]): Binance order parameters.

        Returns:
            dict[str, Any]: Normalized Binance order parameters.
        """
        normalized_params = normalize_order_params_symbol(params)

        side = normalized_params.get("side")

        if side is None:
            raise ValueError("side is required")

        if not isinstance(side, str):
            raise TypeError("side must be a string")

        order_type = normalized_params.get("type")

        if order_type is None:
            raise ValueError("type is required")

        if not isinstance(order_type, str):
            raise TypeError("type must be a string")

        normalized_params["side"] = normalize_order_side(side)
        normalized_params["type"] = order_type.strip().upper()

        return normalized_params

    def _validate_stop_market_quantity(
        self,
        quantity: str | None,
        close_position: bool | None,
    ) -> None:
        """
        Validate quantity requirements for stop market orders.

        Parameters:
            quantity (str | None): Optional order quantity.
            close_position (bool | None): Optional close-position flag.
        """
        if quantity is None and close_position is not True:
            raise ValueError("quantity is required unless close_position is True")

    def ping(self) -> bool:
        """
        Check whether the Binance USD-M Futures REST API is reachable.

        Returns:
            bool: True if the ping request succeeds.
        """
        self._request(
            method="GET",
            path="/v1/ping",
        )

        logger.debug("Binance USD-M Futures ping successful")

        return True

    def get_server_time(self) -> int:
        """
        Return the Binance USD-M Futures server time.

        Returns:
            int: Binance server time in milliseconds.
        """
        data = self._request(
            method="GET",
            path="/v1/time",
        )

        server_time = data["serverTime"]

        if not isinstance(server_time, int):
            raise TypeError(
                "Binance USD-M Futures serverTime response value is not an integer"
            )

        logger.debug(
            "Received Binance USD-M Futures server time server_time=%s",
            server_time,
        )

        return server_time

    def get_account_info(self) -> dict[str, Any]:
        """
        Return Binance USD-M Futures account information.

        Returns:
            dict[str, Any]: Binance USD-M Futures account response.
        """
        account_info = self._signed_request(
            method="GET",
            path="/v3/account",
        )

        logger.debug("Received Binance USD-M Futures account info")

        return account_info

    def get_account_balance(self) -> list[dict[str, Any]]:
        """
        Return Binance USD-M Futures account balances.

        Returns:
            list[dict[str, Any]]: Futures account balance entries.
        """
        return self._signed_request(
            method="GET",
            path="/v3/balance",
        )

    def get_position_risk(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return Binance USD-M Futures position risk entries.

        Parameters:
            symbol (str | None): Optional trading pair symbol.

        Returns:
            list[dict[str, Any]]: Futures position risk entries.
        """
        params: dict[str, Any] = {}

        if symbol is not None:
            params["symbol"] = normalize_symbol(symbol)

        return self._signed_request(
            method="GET",
            path="/v3/positionRisk",
            params=params,
        )

    def get_position_mode(self) -> dict[str, Any]:
        """
        Return Binance USD-M Futures position mode.

        Returns:
            dict[str, Any]: Futures position mode response.
        """
        return self._signed_request(
            method="GET",
            path="/v1/positionSide/dual",
        )

    def change_leverage(
        self,
        symbol: str,
        leverage: int,
    ) -> dict[str, Any]:
        """
        Change leverage for a Binance USD-M Futures symbol.

        Parameters:
            symbol (str): Trading pair symbol.
            leverage (int): Desired leverage value.

        Returns:
            dict[str, Any]: Binance leverage change response.
        """
        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
            "leverage": leverage,
        }

        leverage_result = self._signed_request(
            method="POST",
            path="/v1/leverage",
            params=params,
        )

        logger.info(
            "Changed Binance USD-M Futures leverage symbol=%s leverage=%s",
            params["symbol"],
            leverage,
        )

        return leverage_result

    def change_margin_type(
        self,
        symbol: str,
        margin_type: str,
    ) -> dict[str, Any]:
        """
        Change margin type for a Binance USD-M Futures symbol.

        Parameters:
            symbol (str): Trading pair symbol.
            margin_type (str): Margin type, ISOLATED or CROSSED.

        Returns:
            dict[str, Any]: Binance margin type change response.
        """
        normalized_margin_type = margin_type.strip().upper()

        if normalized_margin_type not in {"ISOLATED", "CROSSED"}:
            raise ValueError("margin_type must be ISOLATED or CROSSED")

        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
            "marginType": normalized_margin_type,
        }

        margin_type_result = self._signed_request(
            method="POST",
            path="/v1/marginType",
            params=params,
        )

        logger.info(
            "Changed Binance USD-M Futures margin type symbol=%s margin_type=%s",
            params["symbol"],
            normalized_margin_type,
        )

        return margin_type_result

    def place_order(
        self,
        params: dict[str, Any],
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place or validate a Binance USD-M Futures order.

        Parameters:
            params (dict[str, Any]): Binance USD-M Futures order parameters.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        if not test and not self.testnet and not ENABLE_TRADING:
            raise RuntimeError(
                "Real futures trading is disabled. "
                "Set ENABLE_TRADING=true to allow live futures orders."
            )

        order_params = self._normalize_order_params(params)

        path = "/v1/order/test" if test else "/v1/order"

        order = self._signed_request(
            method="POST",
            path=path,
            params=order_params,
        )

        logger.info(
            "Placed Binance USD-M Futures order test=%s symbol=%s side=%s type=%s",
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
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures limit order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            quantity (str): Contract quantity.
            price (str): Limit order price.
            time_in_force (str): Order time-in-force policy.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
        }

        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures market order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            quantity (str): Contract quantity.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }

        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        stop_price: str,
        time_in_force: str = "GTC",
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        price_protect: bool | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures stop order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            quantity (str): Contract quantity.
            price (str): Limit order price after trigger.
            stop_price (str): Stop trigger price.
            time_in_force (str): Order time-in-force policy.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            price_protect (bool | None): Optional price protection flag.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "STOP",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
        }

        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            working_type=working_type,
            price_protect=price_protect,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        stop_price: str,
        quantity: str | None = None,
        close_position: bool | None = None,
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        price_protect: bool | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures stop market order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            stop_price (str): Stop trigger price.
            quantity (str | None): Optional contract quantity.
            close_position (bool | None): Optional close-position flag.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            price_protect (bool | None): Optional price protection flag.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        self._validate_stop_market_quantity(
            quantity=quantity,
            close_position=close_position,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
        }

        if quantity is not None:
            params["quantity"] = quantity

        params = self._add_bool_param(
            params=params,
            name="closePosition",
            value=close_position,
        )
        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            working_type=working_type,
            price_protect=price_protect,
            new_order_resp_type=new_order_resp_type,
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
        price: str,
        stop_price: str,
        time_in_force: str = "GTC",
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        price_protect: bool | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures take profit order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            quantity (str): Contract quantity.
            price (str): Limit order price after trigger.
            stop_price (str): Stop trigger price.
            time_in_force (str): Order time-in-force policy.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            price_protect (bool | None): Optional price protection flag.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT",
            "timeInForce": time_in_force,
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
        }

        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            working_type=working_type,
            price_protect=price_protect,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_take_profit_market_order(
        self,
        symbol: str,
        side: str,
        stop_price: str,
        quantity: str | None = None,
        close_position: bool | None = None,
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        price_protect: bool | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures take profit market order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            stop_price (str): Stop trigger price.
            quantity (str | None): Optional contract quantity.
            close_position (bool | None): Optional close-position flag.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            price_protect (bool | None): Optional price protection flag.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        self._validate_stop_market_quantity(
            quantity=quantity,
            close_position=close_position,
        )

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": stop_price,
        }

        if quantity is not None:
            params["quantity"] = quantity

        params = self._add_bool_param(
            params=params,
            name="closePosition",
            value=close_position,
        )
        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            working_type=working_type,
            price_protect=price_protect,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def place_trailing_stop_market_order(
        self,
        symbol: str,
        side: str,
        callback_rate: str,
        quantity: str | None = None,
        activation_price: str | None = None,
        position_side: str | None = None,
        reduce_only: bool | None = None,
        client_order_id: str | None = None,
        working_type: str | None = None,
        new_order_resp_type: str | None = None,
        test: bool = True,
    ) -> dict[str, Any]:
        """
        Place a Binance USD-M Futures trailing stop market order.

        Parameters:
            symbol (str): Trading pair symbol.
            side (str): Order side, BUY or SELL.
            callback_rate (str): Trailing stop callback rate.
            quantity (str | None): Optional contract quantity.
            activation_price (str | None): Optional activation price.
            position_side (str | None): Optional Futures position side.
            reduce_only (bool | None): Optional reduce-only flag.
            client_order_id (str | None): Optional client-defined order ID.
            working_type (str | None): Optional trigger price type.
            new_order_resp_type (str | None): Optional order response type.
            test (bool): Whether to use the validation-only test endpoint.

        Returns:
            dict[str, Any]: Binance order response.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "TRAILING_STOP_MARKET",
            "callbackRate": callback_rate,
        }

        if quantity is not None:
            params["quantity"] = quantity

        params = self._add_optional_param(
            params=params,
            name="activationPrice",
            value=activation_price,
        )
        params = self._add_common_order_params(
            params=params,
            position_side=position_side,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            working_type=working_type,
            new_order_resp_type=new_order_resp_type,
        )

        return self.place_order(
            params=params,
            test=test,
        )

    def get_order(
        self,
        symbol: str,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Return a Binance USD-M Futures order.

        Parameters:
            symbol (str): Trading pair symbol.
            order_id (int | None): Binance-generated order ID.
            client_order_id (str | None): Client-defined order ID.

        Returns:
            dict[str, Any]: Binance order response.
        """
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
            path="/v1/order",
            params=params,
        )

    def get_open_orders(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return open Binance USD-M Futures orders.

        Parameters:
            symbol (str | None): Optional trading pair symbol.

        Returns:
            list[dict[str, Any]]: Open Binance USD-M Futures orders.
        """
        params: dict[str, Any] = {}

        if symbol is not None:
            params["symbol"] = normalize_symbol(symbol)

        return self._signed_request(
            method="GET",
            path="/v1/openOrders",
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
        """
        Return Binance USD-M Futures orders for a symbol.

        Parameters:
            symbol (str): Trading pair symbol.
            limit (int): Maximum number of orders to return.
            order_id (int | None): Optional starting Binance order ID.
            start_time (int | None): Optional start time in milliseconds.
            end_time (int | None): Optional end time in milliseconds.

        Returns:
            list[dict[str, Any]]: Binance USD-M Futures order entries.
        """
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
            path="/v1/allOrders",
            params=params,
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Cancel a Binance USD-M Futures order.

        Parameters:
            symbol (str): Trading pair symbol.
            order_id (int | None): Binance-generated order ID.
            client_order_id (str | None): Client-defined order ID.

        Returns:
            dict[str, Any]: Binance cancellation response.
        """
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
            path="/v1/order",
            params=params,
        )

        logger.info(
            "Canceled Binance USD-M Futures order symbol=%s order_id=%s "
            "client_order_id=%s",
            params["symbol"],
            order_id,
            client_order_id,
        )

        return canceled_order

    def cancel_all_open_orders(
        self,
        symbol: str,
    ) -> dict[str, Any]:
        """
        Cancel all open Binance USD-M Futures orders for a symbol.

        Parameters:
            symbol (str): Trading pair symbol.

        Returns:
            dict[str, Any]: Binance cancellation response.
        """
        params: dict[str, Any] = {
            "symbol": normalize_symbol(symbol),
        }

        canceled_orders = self._signed_request(
            method="DELETE",
            path="/v1/allOpenOrders",
            params=params,
        )

        logger.info(
            "Canceled all Binance USD-M Futures open orders symbol=%s",
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
        """
        Return Binance USD-M Futures account trades for a symbol.

        Parameters:
            symbol (str): Trading pair symbol.
            limit (int): Maximum number of trades to return.
            from_id (int | None): Optional starting trade ID.
            start_time (int | None): Optional start time in milliseconds.
            end_time (int | None): Optional end time in milliseconds.

        Returns:
            list[dict[str, Any]]: Binance USD-M Futures trade entries.
        """
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
            path="/v1/userTrades",
            params=params,
        )
