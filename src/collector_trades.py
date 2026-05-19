import asyncio
import json
import websockets

from config.settings import SYMBOL, DATABASE_PATH
from config.logging_setup import setup_logger
from src.db import connect_db, insert_trade

logger = setup_logger(
    name="trade_collector",
    log_file="logs/trade_collector.log",
)


def trade_stream_url(symbol: str) -> str:
    stream_symbol = symbol.lower()
    return f"wss://stream.binance.com:9443/ws/{stream_symbol}@trade"

async def collect_trades() -> None:
    url = trade_stream_url(SYMBOL)
    conn = connect_db(DATABASE_PATH)

    logger.info("Starting trade collector")
    logger.info("Symbol: %s", SYMBOL)
    logger.info("Database path: %s", DATABASE_PATH)
    logger.info("WebSocket URL: %s", url)

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as websocket:
                print("Connect.")

                async for message in websocket:
                    msg = json.loads(message)
                    
                    insert_trade(conn, msg)


        except Exception as exc:
            logger.exception("WebSocket error. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(collect_trades())