# Run the live trade collector and consume its queue.
"""
Provide the minimal live runner.

This module starts the live trade collector as an asyncio task, receives
normalized live trades through an asyncio queue, determines the first live
trade per symbol, and keeps consuming the stream without doing feature
calculation yet.
"""

import asyncio
import contextlib

from config.logging_setup import setup_logger
from config.settings import (
    CUTOVER_TIMEOUT_SECONDS,
    STATUS_LOG_INTERVAL_SECONDS,
    SYMBOLS,
    TRADE_QUEUE_MAX_SIZE,
)
from src.live.live_bootstrap import collect_first_live_trades
from src.live.live_collector import (
    LiveCollectorStatus,
    LiveTradeEvent,
    collect_live_trades,
)
from src.live.trade_processor import run_trade_processor

logger = setup_logger(name="main_live", log_file="logs/main_live.log")


async def run_live(
    symbols: list[str],
    trade_queue_max_size: int,
    cutover_timeout_seconds: float,
    status_log_interval_seconds: float,
) -> None:
    """
    Start the live collector and consume live trades.

    Parameters:
        symbols (list[str]): Trading pair symbols.
        trade_queue_max_size (int): Maximum number of queued live trades.
        cutover_timeout_seconds (float): Maximum wait time for first live trades.
        status_log_interval_seconds (float): Interval for aggregate status logs.
    """
    trade_queue: asyncio.Queue[LiveTradeEvent] = asyncio.Queue(
        maxsize=trade_queue_max_size,
    )
    status = LiveCollectorStatus()

    logger.info("Starting main live runner symbols=%s", ", ".join(symbols))

    collector_task = asyncio.create_task(
        collect_live_trades(
            symbols=symbols,
            trade_queue=trade_queue,
            status=status,
        ),
        name="live_collector",
    )

    consumer_task: asyncio.Task[None] | None = None

    try:
        first_trade_id_by_symbol, buffered_trades = await collect_first_live_trades(
            symbols=symbols,
            trade_queue=trade_queue,
            timeout_seconds=cutover_timeout_seconds,
        )

        logger.info(
            "Bootstrap cutover ready first_trade_id_by_symbol=%s buffered_trades=%d",
            first_trade_id_by_symbol,
            len(buffered_trades),
        )

        logger.info(
            "Buffered trades are available for later replay. "
            "Starting normal queue consumption."
        )

        consumer_task = asyncio.create_task(
            run_trade_processor(
                trade_queue=trade_queue,
                status=status,
                status_log_interval_seconds=status_log_interval_seconds,
            ),
            name="live_consumer",
        )

        await consumer_task

    except asyncio.CancelledError:
        logger.info("Main live runner cancellation requested")
        raise

    finally:
        logger.info("Stopping main live runner")

        if consumer_task is not None:
            consumer_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task

        collector_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await collector_task

        logger.info(
            "Main live runner stopped collector_received_messages=%d "
            "collector_queued_trades=%d collector_reconnect_count=%d",
            status.received_message_count,
            status.queued_trade_count,
            status.reconnect_count,
        )


def main() -> None:
    """
    Run the live runner entrypoint.
    """
    asyncio.run(
        run_live(
            symbols=SYMBOLS,
            trade_queue_max_size=TRADE_QUEUE_MAX_SIZE,
            cutover_timeout_seconds=CUTOVER_TIMEOUT_SECONDS,
            status_log_interval_seconds=STATUS_LOG_INTERVAL_SECONDS,
        )
    )


if __name__ == "__main__":
    main()
