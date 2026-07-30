# Collect Binance live trades into an asyncio queue.
"""
Provide the live WebSocket trade collector.

This module connects to Binance combined trade streams, normalizes incoming
trade messages, forwards them into an asyncio queue, and exposes a lightweight
status object for the live runner.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field

import websockets
from config.logging_setup import setup_logger
from src.collector_trades import trade_stream_url

RECONNECT_DELAY_SECONDS = 5
QUEUE_FULL_LOG_INTERVAL_SECONDS = 5.0

logger = setup_logger(name="live_collector", log_file="logs/live_collector.log")


@dataclass(frozen=True, slots=True)
class LiveTradeEvent:
    """
    A normalized live trade event from the Binance trade stream.

    Attributes:
        symbol (str): Trading pair symbol.
        event_time_ms (int): Binance event timestamp in milliseconds.
        trade_time_ms (int): Binance trade timestamp in milliseconds.
        exchange_trade_id (int): Binance exchange trade identifier.
        price (float): Trade price.
        quantity (float): Trade quantity.
        is_buyer_maker (bool): Whether the buyer is the maker.
        connection_id (int): Collector connection generation identifier.
        received_monotonic (float): Local monotonic receive timestamp.
    """

    symbol: str
    event_time_ms: int
    trade_time_ms: int
    exchange_trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool
    connection_id: int
    received_monotonic: float


@dataclass(slots=True)
class LiveCollectorStatus:
    """
    Runtime status for the live collector.

    Attributes:
        running (bool): Whether the collector task is active.
        connected (bool): Whether the WebSocket is currently connected.
        connection_id (int): Current connection generation identifier.
        reconnect_count (int): Number of reconnect attempts after failures.
        received_message_count (int): Number of received WebSocket messages.
        queued_trade_count (int): Number of trades successfully put into the queue.
        parse_error_count (int): Number of invalid messages that were skipped.
        queue_full_count (int): Number of times the output queue was observed full.
        last_message_monotonic (float | None): Last local message receive time.
        last_connection_started_monotonic (float | None): Last connection start time.
        last_disconnect_monotonic (float | None): Last disconnect time.
        last_error (str | None): Last collector error as text.
        last_trade_id_by_symbol (dict[str, int]): Last seen trade ID per symbol.
        last_trade_time_ms_by_symbol (dict[str, int]): Last seen trade time per symbol.
    """

    running: bool = False
    connected: bool = False
    connection_id: int = 0
    reconnect_count: int = 0
    received_message_count: int = 0
    queued_trade_count: int = 0
    parse_error_count: int = 0
    queue_full_count: int = 0
    last_message_monotonic: float | None = None
    last_connection_started_monotonic: float | None = None
    last_disconnect_monotonic: float | None = None
    last_error: str | None = None
    last_trade_id_by_symbol: dict[str, int] = field(default_factory=dict)
    last_trade_time_ms_by_symbol: dict[str, int] = field(default_factory=dict)


def parse_live_trade_event(
    message: str,
    connection_id: int,
    received_monotonic: float,
) -> LiveTradeEvent:
    """
    Parse and normalize one Binance combined trade stream message.

    Parameters:
        message (str): Raw WebSocket message as JSON string.
        connection_id (int): Collector connection generation identifier.
        received_monotonic (float): Local monotonic receive timestamp.

    Returns:
        LiveTradeEvent: Normalized live trade event.

    Raises:
        ValueError: If the message is not a Binance trade message.
        KeyError: If a required trade field is missing.
        TypeError: If a required field has an invalid type.
        json.JSONDecodeError: If the message is not valid JSON.
    """
    raw_message = json.loads(message)
    data = raw_message.get("data")

    if not isinstance(data, dict):
        raise ValueError("Combined stream message is missing a data object")

    if data.get("e") != "trade":
        raise ValueError(f"Unexpected stream event type: {data.get('e')}")

    is_buyer_maker = data["m"]

    if not isinstance(is_buyer_maker, bool):
        raise TypeError("Trade field 'm' must be a boolean")

    return LiveTradeEvent(
        symbol=str(data["s"]).upper(),
        event_time_ms=int(data["E"]),
        trade_time_ms=int(data["T"]),
        exchange_trade_id=int(data["t"]),
        price=float(data["p"]),
        quantity=float(data["q"]),
        is_buyer_maker=is_buyer_maker,
        connection_id=connection_id,
        received_monotonic=received_monotonic,
    )


async def collect_live_trades(
    symbols: list[str],
    trade_queue: asyncio.Queue[LiveTradeEvent],
    status: LiveCollectorStatus,
) -> None:
    """
    Collect live Binance trades and forward them into an asyncio queue.

    Parameters:
        symbols (list[str]): Trading pair symbols.
        trade_queue (asyncio.Queue[LiveTradeEvent]): Queue receiving live trades.
        status (LiveCollectorStatus): Mutable collector status shared with caller.
    """
    if not symbols:
        raise ValueError("symbols must not be empty")

    url = trade_stream_url(symbols)
    last_queue_full_log = 0.0

    status.running = True

    logger.info("Starting live collector")
    logger.info("Symbols: %s", ", ".join(symbols))
    logger.info("WebSocket URL: %s", url)

    try:
        while True:
            status.connection_id += 1
            connection_id = status.connection_id

            try:
                async with websockets.connect(
                    url,
                    ping_interval=30,
                    ping_timeout=30,
                    close_timeout=10,
                ) as websocket:
                    status.connected = True
                    status.last_error = None
                    status.last_connection_started_monotonic = time.monotonic()

                    logger.info(
                        "Connected to Binance WebSocket connection_id=%d",
                        connection_id,
                    )

                    async for message in websocket:
                        received_monotonic = time.monotonic()

                        status.received_message_count += 1
                        status.last_message_monotonic = received_monotonic

                        try:
                            trade = parse_live_trade_event(
                                message=message,
                                connection_id=connection_id,
                                received_monotonic=received_monotonic,
                            )
                        except Exception:
                            status.parse_error_count += 1

                            logger.exception(
                                "Failed parsing live trade message "
                                "connection_id=%d parse_error_count=%d",
                                connection_id,
                                status.parse_error_count,
                            )
                            continue

                        if trade_queue.full():
                            status.queue_full_count += 1

                            if (
                                received_monotonic - last_queue_full_log
                                >= QUEUE_FULL_LOG_INTERVAL_SECONDS
                            ):
                                logger.warning(
                                    "Live trade queue is full queue_size=%d "
                                    "maxsize=%d queue_full_count=%d",
                                    trade_queue.qsize(),
                                    trade_queue.maxsize,
                                    status.queue_full_count,
                                )
                                last_queue_full_log = received_monotonic

                        await trade_queue.put(trade)

                        status.queued_trade_count += 1
                        status.last_trade_id_by_symbol[trade.symbol] = (
                            trade.exchange_trade_id
                        )
                        status.last_trade_time_ms_by_symbol[trade.symbol] = (
                            trade.trade_time_ms
                        )

            except asyncio.CancelledError:
                logger.info("Live collector cancellation requested")
                raise

            except Exception as exc:
                status.connected = False
                status.reconnect_count += 1
                status.last_disconnect_monotonic = time.monotonic()
                status.last_error = repr(exc)

                logger.exception(
                    "Live WebSocket error connection_id=%d reconnect_count=%d. "
                    "Reconnecting in %d seconds...",
                    connection_id,
                    status.reconnect_count,
                    RECONNECT_DELAY_SECONDS,
                )

                await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    finally:
        status.running = False
        status.connected = False

        logger.info(
            "Live collector stopped received_messages=%d queued_trades=%d "
            "reconnect_count=%d parse_error_count=%d queue_full_count=%d",
            status.received_message_count,
            status.queued_trade_count,
            status.reconnect_count,
            status.parse_error_count,
            status.queue_full_count,
        )
