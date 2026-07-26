import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_bool_env(name: str) -> bool:
    value = os.getenv(name)

    if value is None:
        raise ValueError(f"{name} is missing in .env file")

    value = value.strip().lower()

    if value == "true":
        return True

    if value == "false":
        return False

    raise ValueError(f"{name} must be 'true' or 'false'")


BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

BINANCE_API_KEY_TESTNET = os.getenv("BINANCE_API_KEY_TESTNET")
BINANCE_API_SECRET_TESTNET = os.getenv("BINANCE_API_SECRET_TESTNET")

BINANCE_TESTNET = get_bool_env("BINANCE_TESTNET")
ENABLE_TRADING = get_bool_env("ENABLE_TRADING")


SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv("SYMBOLS", "BTCUSDT").split(",")
    if symbol.strip()
]

RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "data/processed"))

TRADE_SIZE_USDT = float(os.getenv("TRADE_SIZE_USDT", float(25)))
