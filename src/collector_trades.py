import asyncio
import json
import time
import websockets

from config.settings import SYMBOL, DATABASE_DIR
from config.logging_setup import setup_logger
from src.db import connect_db, insert_trades, daily_database_path

#Code saves the trades into the db after BATCH_SIZE-trades or FLUSH_INTERVAL_SECONDS-seconds
BATCH_SIZE = 250
FLUSH_INTERVAL_SECONDS = 1.0 #Saves the trades every second

logger = setup_logger(
    name="trade_collector",
    log_file="logs/trade_collector.log",
)


def trade_stream_url(symbol: str) -> str:
    stream_symbol = symbol.lower()
    return f"wss://stream.binance.com:9443/ws/{stream_symbol}@trade"

async def collect_trades() -> None:
    url = trade_stream_url(SYMBOL)

    current_db_path = daily_database_path(DATABASE_DIR)
    conn = connect_db(current_db_path)

    buffer: list[dict] = []
    last_flush = time.monotonic()
    total_received = 0
    total_flushed = 0

    logger.info("Starting trade collector")
    logger.info("Symbol: %s", SYMBOL)
    logger.info("Database path: %s", current_db_path)
    logger.info("WebSocket URL: %s", url)

    try:
        while True:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=30,
                    ping_timeout=30,
                    close_timeout=10,
                ) as websocket:
                    logger.info("Connected to Binance WebSocket")

                    async for message in websocket:
                        msg = json.loads(message)
                        buffer.append(msg)
                        total_received += 1

                        new_db_path = daily_database_path(DATABASE_DIR)

                        if new_db_path != current_db_path:
                            if buffer:
                                insert_trades(conn, buffer)
                                total_flushed += len(buffer)
                                buffer.clear()

                            conn.close()
                            current_db_path = new_db_path
                            conn = connect_db(current_db_path)
                            last_flush = time.monotonic()

                            logger.info("Rotated database to %s", current_db_path)

                        now = time.monotonic()

                        should_flush_by_size = len(buffer) >= BATCH_SIZE
                        should_flush_by_time = (now - last_flush) >= FLUSH_INTERVAL_SECONDS

                        if should_flush_by_size or should_flush_by_time:
                            batch_size = len(buffer)
                            insert_trades(conn, buffer)
                            total_flushed += batch_size

                            last_msg = buffer[-1]
                            buffer.clear()
                            last_flush = now

                            logger.debug(
                                "Stored batch=%d total_received=%d total_flushed=%d "
                                "last_trade_id=%s price=%s quantity=%s",
                                batch_size,
                                total_received,
                                total_flushed,
                                last_msg["t"],
                                last_msg["p"],
                                last_msg["q"],
                            )

            except Exception:
                logger.exception("WebSocket error. Reconnecting in 5 seconds...")

                if buffer:
                    try:
                        batch_size = len(buffer)
                        insert_trades(conn, buffer)
                        total_flushed += batch_size
                        buffer.clear()

                        logger.info(
                            "Flushed %d buffered trades after error. total_flushed=%d",
                            batch_size,
                            total_flushed,
                        )
                    except Exception:
                        logger.exception("Failed to flush buffered trades after error")

                await asyncio.sleep(5)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")

    finally:
        if buffer:
            try:
                batch_size = len(buffer)
                insert_trades(conn, buffer)
                total_flushed += batch_size
                buffer.clear()

                logger.info(
                    "Flushed final buffer with %d trades. total_flushed=%d",
                    batch_size,
                    total_flushed,
                )
            except Exception:
                logger.exception("Failed to flush final buffer during shutdown")

        conn.close()

        logger.info(
            "Collector stopped cleanly. total_received=%d total_flushed=%d",
            total_received,
            total_flushed,
        )


if __name__ == "__main__":
    asyncio.run(collect_trades())