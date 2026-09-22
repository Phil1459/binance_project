from dataclasses import dataclass, field


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
