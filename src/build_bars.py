# Build 15-second OHLCV bars from raw trade databases.
"""
Provide the bar build pipeline.

This module reads raw SQLite trade files and writes per-symbol 15-second bar
Parquet files.
"""

import sqlite3
from pathlib import Path

import pandas as pd
from config.logging_setup import setup_logger
from config.settings import PROCESSED_DIR, RAW_DIR

BAR_INTERVAL = "15s"
BAR_INTERVAL_MS = 15_000


logger = setup_logger(
    name="build_bars",
    log_file="logs/build_bars.log",
)


def extract_date_part(raw_db_path: Path) -> str:
    """
    Extract the date part from a raw trade database path.

    Parameters:
        raw_db_path (Path): Raw SQLite database path.

    Returns:
        str: Date part from the database filename.
    """
    return raw_db_path.stem.replace("trades_", "")


def get_symbols(conn: sqlite3.Connection) -> list[str]:
    """
    Return all symbols contained in a raw trade database.

    Parameters:
        conn (sqlite3.Connection): Open SQLite database connection.

    Returns:
        list[str]: Sorted list of symbols.
    """
    rows = conn.execute("""
        SELECT DISTINCT symbol
        FROM trades
        ORDER BY symbol;
    """).fetchall()

    return [row[0] for row in rows]


def output_path_for(symbol: str, date_part: str) -> Path:
    """
    Return the output path for one symbol and date.

    Parameters:
        symbol (str): Trading pair symbol.
        date_part (str): Date part from the raw database filename.

    Returns:
        Path: Target Parquet output path.
    """
    return (
        PROCESSED_DIR
        / f"bars_{BAR_INTERVAL}"
        / symbol
        / f"bars_{BAR_INTERVAL}_{symbol}_{date_part}.parquet"
    )


def build_bars_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    date_part: str,
    output_path: Path,
) -> None:
    """
    Build and save bars for one symbol from a raw database.

    Parameters:
        conn (sqlite3.Connection): Open SQLite database connection.
        symbol (str): Trading pair symbol.
        date_part (str): Date part from the raw database filename.
        output_path (Path): Target Parquet output path.
    """
    logger.info(
        "Building bars interval=%s symbol=%s date=%s output=%s",
        BAR_INTERVAL,
        symbol,
        date_part,
        output_path,
    )

    query = f"""
    WITH symbol_trades AS (
        SELECT
            symbol,
            trade_time,
            exchange_trade_id,
            price,
            quantity,
            is_buyer_maker
        FROM trades
        WHERE symbol = ?
    ),
    bucketed AS (
        SELECT
            symbol,
            (trade_time / {BAR_INTERVAL_MS}) * {BAR_INTERVAL_MS} AS bucket_time,
            trade_time,
            exchange_trade_id,
            price,
            quantity,
            is_buyer_maker
        FROM symbol_trades
    ),
    base AS (
        SELECT
            symbol,
            bucket_time,
            MIN(price) AS low,
            MAX(price) AS high,
            SUM(price * quantity) / SUM(quantity) AS vwap,
            SUM(quantity) AS volume,
            SUM(CASE WHEN is_buyer_maker = 0 THEN quantity ELSE 0 END) AS buy_volume,
            SUM(CASE WHEN is_buyer_maker = 1 THEN quantity ELSE 0 END) AS sell_volume,
            COUNT(*) AS trade_count
        FROM bucketed
        GROUP BY symbol, bucket_time
    ),
    open_close_times AS (
        SELECT
            symbol,
            bucket_time,
            MIN(exchange_trade_id) AS open_trade_id,
            MAX(exchange_trade_id) AS close_trade_id
        FROM bucketed
        GROUP BY symbol, bucket_time
    ),
    opens AS (
        SELECT
            b.symbol,
            b.bucket_time,
            b.price AS open
        FROM bucketed b
        JOIN open_close_times oct
            ON b.symbol = oct.symbol
            AND b.bucket_time = oct.bucket_time
            AND b.exchange_trade_id = oct.open_trade_id
    ),
    closes AS (
        SELECT
            b.symbol,
            b.bucket_time,
            b.price AS close
        FROM bucketed b
        JOIN open_close_times oct
            ON b.symbol = oct.symbol
            AND b.bucket_time = oct.bucket_time
            AND b.exchange_trade_id = oct.close_trade_id
    )
    SELECT
        base.symbol,
        datetime(base.bucket_time / 1000, 'unixepoch') AS timestamp,
        opens.open,
        base.high,
        base.low,
        closes.close,
        base.vwap,
        base.volume,
        base.buy_volume,
        base.sell_volume,
        base.trade_count
    FROM base
    JOIN opens
        ON base.symbol = opens.symbol
        AND base.bucket_time = opens.bucket_time
    JOIN closes
        ON base.symbol = closes.symbol
        AND base.bucket_time = closes.bucket_time
    ORDER BY base.bucket_time;
    """

    df = pd.read_sql_query(query, conn, params=(symbol,))

    if df.empty:
        logger.warning(
            "No bars created interval=%s symbol=%s date=%s",
            BAR_INTERVAL,
            symbol,
            date_part,
        )
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    logger.info(
        "Saved bars interval=%s symbol=%s date=%s rows=%d start=%s end=%s output=%s",
        BAR_INTERVAL,
        symbol,
        date_part,
        len(df),
        df["timestamp"].min(),
        df["timestamp"].max(),
        output_path,
    )


def build_bars_for_file(raw_db_path: Path) -> None:
    """
    Build bars for every symbol in one raw database file.

    Parameters:
        raw_db_path (Path): Raw SQLite database path.
    """
    date_part = extract_date_part(raw_db_path)

    logger.info(
        "Processing raw database date=%s path=%s",
        date_part,
        raw_db_path,
    )

    with sqlite3.connect(raw_db_path) as conn:
        logger.debug(
            "Opened database path=%s",
            raw_db_path,
        )

        # To reduce runtime
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-200000;")

        symbols = get_symbols(conn)

        if not symbols:
            logger.warning(
                "No symbols found date=%s path=%s",
                date_part,
                raw_db_path,
            )
            return

        logger.info(
            "Found symbols date=%s symbols=%s",
            date_part,
            ", ".join(symbols),
        )

        for symbol in symbols:
            output_path = output_path_for(symbol, date_part)

            if output_path.exists():
                logger.info(
                    "Skipping existing bars interval=%s symbol=%s date=%s output=%s",
                    BAR_INTERVAL,
                    symbol,
                    date_part,
                    output_path,
                )
                continue

            build_bars_for_symbol(
                conn=conn,
                symbol=symbol,
                date_part=date_part,
                output_path=output_path,
            )


def main() -> None:
    """
    Run the bar build pipeline for all raw databases.
    """
    logger.info(
        "Starting bar build pipeline raw_dir=%s processed_dir=%s interval=%s",
        RAW_DIR,
        PROCESSED_DIR,
        BAR_INTERVAL,
    )

    raw_files = sorted(RAW_DIR.glob("trades_*.sqlite"))

    if not raw_files:
        logger.warning(
            "No raw SQLite files found raw_dir=%s",
            RAW_DIR,
        )
        return

    logger.info(
        "Found raw SQLite files count=%d",
        len(raw_files),
    )

    for raw_db_path in raw_files:
        try:
            build_bars_for_file(raw_db_path)
        except Exception:
            logger.exception(
                "Failed processing raw database path=%s",
                raw_db_path,
            )

    logger.info("Finished bar build pipeline")


if __name__ == "__main__":
    main()
