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
    if testnet:
        return BASE_URL_SPOT_REST_LIVE[0]

    return BASE_URL_SPOT_REST_TESTNET[0]
