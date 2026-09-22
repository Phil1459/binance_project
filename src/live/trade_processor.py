import asyncio
import time

from config.logging_setup import setup_logger
from src.live.live_types import (
    LiveCollectorStatus,
    LiveTradeEvent,
)

logger = setup_logger(name="trade_processor", log_file="logs/trade_processor.log")


async def run_trade_processor(
    trade_queue: asyncio.Queue[LiveTradeEvent],
    status: LiveCollectorStatus,
    status_log_interval_seconds: float,
) -> None:
    """
    Consume live trades from the queue and log aggregate runtime status.

    Parameters:
        trade_queue (asyncio.Queue[LiveTradeEvent]): Queue receiving live trades.
        status (LiveCollectorStatus): Shared live collector status.
        status_log_interval_seconds (float): Interval for aggregate status logs.
    """
    consumed_count = 0
    last_log_monotonic = time.monotonic()

    while True:
        _trade = await trade_queue.get()
        consumed_count += 1
        trade_queue.task_done()

        now = time.monotonic()

        if now - last_log_monotonic >= status_log_interval_seconds:
            last_message_age = None

            if status.last_message_monotonic is not None:
                last_message_age = now - status.last_message_monotonic

            logger.info(
                "Live runner status consumed_trades=%d queue_size=%d "
                "collector_connected=%s reconnect_count=%d "
                "received_messages=%d queued_trades=%d last_message_age=%s",
                consumed_count,
                trade_queue.qsize(),
                status.connected,
                status.reconnect_count,
                status.received_message_count,
                status.queued_trade_count,
                (
                    f"{last_message_age:.3f}s"
                    if last_message_age is not None
                    else "None"
                ),
            )

            last_log_monotonic = now
