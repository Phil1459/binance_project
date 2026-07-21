import logging
from typing import Any

from config.settings import (
    BINANCE_API_KEY,
    BINANCE_API_KEY_TESTNET,
    BINANCE_API_SECRET,
    BINANCE_API_SECRET_TESTNET,
    BINANCE_TESTNET,
)
from src.binance.base_client import BaseClientRest
from src.binance.endpoints import get_base_url_spot_rest

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
