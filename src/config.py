from dotenv import load_dotenv
import os

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

BINANCE_TESTNET = os.getenv("BINANCE_TESTNET") == "true"

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")

ENABLE_TRADING = os.getenv("ENABLE_TRADING") == "true"

TRADE_SIZE_USDT = float(os.getenv("TRADE_SIZE_USDT", 25))