# Collect Binance trade stream data into daily SQLite databases.
"""
Provide the live trade collector.

This module connects to Binance trade WebSocket streams and stores incoming
trades in daily raw SQLite database files.
"""

import asyncio
import json
import time

import websockets
from config.logging_setup import setup_logger
from config.settings import RAW_DIR, SYMBOLS
from src.db import connect_db, daily_database_path, insert_trades

# Code saves the trades into the db after
# BATCH_SIZE-trades or FLUSH_INTERVAL_SECONDS-seconds
BATCH_SIZE = 250
FLUSH_INTERVAL_SECONDS = 1.0  # Saves the trades every second

logger = setup_logger(
    name="trade_collector",
    log_file="logs/trade_collector.log",
)


def trade_stream_url(symbols: list[str]) -> str:
    """
    Build a Binance combined trade stream URL.

    Parameters:
        symbols (list[str]): Trading pair symbols.

    Returns:
        str: Binance combined WebSocket trade stream URL.
    """
    streams = "/".join(f"{symbol.lower()}@trade" for symbol in symbols)
    return f"wss://stream.binance.com:9443/stream?streams={streams}"


async def collect_trades() -> None:
    """
    Collect Binance trades and store them in daily SQLite databases.
    """
    url = trade_stream_url(SYMBOLS)

    current_db_path = daily_database_path(RAW_DIR)
    conn = connect_db(current_db_path)

    buffer: list[dict] = []
    last_flush = time.monotonic()

    total_received = 0
    total_flushed = 0

    logger.info("Starting trade collector")
    logger.info("Symbols: %s", ", ".join(SYMBOLS))
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
                        raw_msg = json.loads(message)

                        # Combined streams wrap the trade payload in "data"
                        msg = raw_msg["data"]

                        buffer.append(msg)
                        total_received += 1

                        new_db_path = daily_database_path(RAW_DIR)

                        if new_db_path != current_db_path:
                            if buffer:
                                batch_size = len(buffer)
                                insert_trades(conn, buffer)
                                total_flushed += batch_size
                                buffer.clear()

                            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                            conn.close()

                            current_db_path = new_db_path
                            conn = connect_db(current_db_path)
                            last_flush = time.monotonic()

                            logger.info("Rotated database to %s", current_db_path)

                        now = time.monotonic()

                        should_flush_by_size = len(buffer) >= BATCH_SIZE
                        should_flush_by_time = (
                            now - last_flush
                        ) >= FLUSH_INTERVAL_SECONDS

                        if should_flush_by_size or should_flush_by_time:
                            batch_size = len(buffer)
                            insert_trades(conn, buffer)
                            total_flushed += batch_size
                            buffer.clear()
                            last_flush = now

                            logger.debug(
                                "Stored batch=%d total_received=%d total_flushed=%d",
                                batch_size,
                                total_received,
                                total_flushed,
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

        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.close()

        logger.info(
            "Collector stopped cleanly. total_received=%d total_flushed=%d",
            total_received,
            total_flushed,
        )


if __name__ == "__main__":
    asyncio.run(collect_trades())
