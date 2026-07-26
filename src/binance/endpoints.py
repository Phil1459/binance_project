# Binance REST endpoint configuration.
"""
Provide Binance REST base URLs.

This module contains live and testnet base URLs for Spot and USD-M Futures REST
clients.
"""

# Spot APIs
BASE_URL_SPOT_REST_LIVE = [
    "https://api.binance.com/api",
    "https://api-gcp.binance.com/api",
    "https://api1.binance.com/api",
    "https://api2.binance.com/api",
    "https://api3.binance.com/api",
    "https://api4.binance.com/api",
]


BASE_URL_SPOT_REST_TESTNET = [
    "https://testnet.binance.vision/api",
    "https://api1.testnet.binance.vision/api",
]


def get_base_url_spot_rest(testnet: bool) -> str:
    """
    Return the Binance Spot REST base URL.

    Parameters:
        testnet (bool): Whether to use the Spot testnet base URL.

    Returns:
        str: Binance Spot REST base URL.
    """
    if testnet:
        return BASE_URL_SPOT_REST_TESTNET[0]

    return BASE_URL_SPOT_REST_LIVE[0]


# Futures against USDT API
USD_M_FUTURES_REST_LIVE_BASE_URLS = [
    "https://fapi.binance.com/fapi",
]

USD_M_FUTURES_REST_TESTNET_BASE_URLS = [
    "https://testnet.binancefuture.com/fapi",
]


def get_base_url_usd_m_futures_rest(testnet: bool) -> str:
    """
    Return the Binance USD-M Futures REST base URL.

    Parameters:
        testnet (bool): Whether to use the USD-M Futures testnet base URL.

    Returns:
        str: Binance USD-M Futures REST base URL.
    """
    if testnet:
        return USD_M_FUTURES_REST_TESTNET_BASE_URLS[0]

    return USD_M_FUTURES_REST_LIVE_BASE_URLS[0]
