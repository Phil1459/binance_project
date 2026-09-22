import asyncio
import time

from config.logging_setup import setup_logger
from src.live.live_collector import (
    LiveTradeEvent,
)

logger = setup_logger(name="live_bootstrap", log_file="logs/live_bootstrap.log")


async def collect_first_live_trades(
    symbols: list[str],
    trade_queue: asyncio.Queue[LiveTradeEvent],
    timeout_seconds: float,
) -> tuple[dict[str, int], list[LiveTradeEvent]]:
    """
    Collect the first live trade ID for every configured symbol.

    Parameters:
        symbols (list[str]): Trading pair symbols expected in the live stream.
        trade_queue (asyncio.Queue[LiveTradeEvent]): Queue receiving live trades.
        timeout_seconds (float): Maximum time to wait for all symbols.

    Returns:
        tuple[dict[str, int], list[LiveTradeEvent]]: First live trade ID per symbol
        and all trades buffered while waiting.

    Raises:
        TimeoutError: If no first live trade was received for every symbol.
    """
    expected_symbols = {symbol.upper() for symbol in symbols}
    first_trade_id_by_symbol: dict[str, int] = {}
    buffered_trades: list[LiveTradeEvent] = []

    deadline = time.monotonic() + timeout_seconds

    logger.debug(
        "Waiting for first live trade per symbol symbols=%s timeout_seconds=%.1f",
        ", ".join(sorted(expected_symbols)),
        timeout_seconds,
    )

    while set(first_trade_id_by_symbol) != expected_symbols:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            missing_symbols = sorted(expected_symbols - set(first_trade_id_by_symbol))
            raise TimeoutError(
                "Timed out waiting for first live trades. "
                f"missing_symbols={missing_symbols}"
            )

        trade = await asyncio.wait_for(trade_queue.get(), timeout=remaining)
        buffered_trades.append(trade)
        trade_queue.task_done()

        if trade.symbol not in expected_symbols:
            logger.warning(
                "Received unexpected live trade symbol=%s trade_id=%d",
                trade.symbol,
                trade.exchange_trade_id,
            )
            continue

        if trade.symbol not in first_trade_id_by_symbol:
            first_trade_id_by_symbol[trade.symbol] = trade.exchange_trade_id

            logger.info(
                "Captured first live trade symbol=%s trade_id=%d trade_time_ms=%d",
                trade.symbol,
                trade.exchange_trade_id,
                trade.trade_time_ms,
            )

    logger.info(
        "Captured first live trades symbols=%s buffered_trades=%d",
        ", ".join(
            f"{symbol}:{trade_id}"
            for symbol, trade_id in sorted(first_trade_id_by_symbol.items())
        ),
        len(buffered_trades),
    )

    return first_trade_id_by_symbol, buffered_trades
