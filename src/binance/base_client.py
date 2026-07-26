import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


class BaseClientRest:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 10,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"

        logger.debug(
            "Sending Binance REST request method=%s url=%s params=%s",
            method,
            url,
            params,
        )

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException:
            logger.exception(
                "Binance REST request failed before response "
                "method=%s url=%s params=%s",
                method,
                url,
                params,
            )
            raise

        if response.status_code >= 400:
            logger.error(
                "Binance REST request failed status=%s response=%s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        if response.text == "":
            return {}

        return response.json()

    def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        self._require_credentials()

        assert self.api_key is not None

        signed_params = dict(params or {})

        signed_params["timestamp"] = int(time.time() * 1000)
        signed_params["recvWindow"] = 5000

        query_string = urlencode(signed_params)
        signature = self._sign(query_string=query_string)

        signed_params["signature"] = signature

        headers = {
            "X-MBX-APIKEY": self.api_key,
        }

        return self._request(
            method=method,
            path=path,
            params=signed_params,
            headers=headers,
        )

    def _sign(self, query_string: str) -> str:
        self._require_credentials()

        assert self.api_secret is not None

        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _require_credentials(self) -> None:
        if not self.api_key:
            raise ValueError("Binance API key is required for signed requests")

        if not self.api_secret:
            raise ValueError("Binance API secret is required for signed requests")
