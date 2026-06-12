from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

BINANCE_TESTNET = os.getenv("BINANCE_TESTNET") == "true"

SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv("SYMBOLS", "BTCUSDT").split(",")
    if symbol.strip()
]

RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "data/processed"))


ENABLE_TRADING = os.getenv("ENABLE_TRADING") == "true"

TRADE_SIZE_USDT = float(os.getenv("TRADE_SIZE_USDT", float(25)))