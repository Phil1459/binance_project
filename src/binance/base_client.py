# Shared REST base client for Binance API clients.
"""
Provide shared Binance REST request functionality.

This module contains unsigned requests, signed requests, HMAC signing, and
credential validation for Binance REST clients.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


class BaseClientRest:
    """
    A base client for Binance REST requests.

    Attributes:
        base_url (str): Binance REST base URL.
        timeout_seconds (int): HTTP request timeout in seconds.
        api_key (str | None): Binance API key for signed requests.
        api_secret (str | None): Binance API secret for signed requests.
        session (requests.Session): HTTP session used for REST requests.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 10,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        """
        Initialize a Binance REST base client.

        Parameters:
            base_url (str): Binance REST base URL.
            timeout_seconds (int): HTTP request timeout in seconds.
            api_key (str | None): Binance API key for signed requests.
            api_secret (str | None): Binance API secret for signed requests.
        """
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
        """
        Send a Binance REST request.

        Parameters:
            method (str): HTTP request method.
            path (str): REST endpoint path.
            params (dict[str, Any] | None): Query parameters.
            headers (dict[str, str] | None): HTTP request headers.

        Returns:
            Any: Parsed Binance JSON response.
        """
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
        """
        Send a signed Binance REST request.

        Parameters:
            method (str): HTTP request method.
            path (str): REST endpoint path.
            params (dict[str, Any] | None): Unsigned query parameters.

        Returns:
            Any: Parsed Binance JSON response.
        """
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
        """
        Create a Binance HMAC SHA256 signature.

        Parameters:
            query_string (str): URL-encoded query string to sign.

        Returns:
            str: Hexadecimal request signature.
        """
        self._require_credentials()

        assert self.api_secret is not None

        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _require_credentials(self) -> None:
        """
        Validate that API credentials are available.
        """
        if not self.api_key:
            raise ValueError("Binance API key is required for signed requests")

        if not self.api_secret:
            raise ValueError("Binance API secret is required for signed requests")
