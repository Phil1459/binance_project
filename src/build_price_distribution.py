# Build 1-second price distributions from raw trade databases.
"""
Provide the price distribution build pipeline.

This module reads raw SQLite trade files and writes per-symbol 1-second price
distribution Parquet files.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
from config.logging_setup import setup_logger
from config.settings import PROCESSED_DIR, RAW_DIR

INTERVAL = "1s"
INTERVAL_MS = 1_000
PRICE_BUCKET_SIZE = 1
FETCH_SIZE = 50_000


logger = setup_logger(
    name="build_price_distributions",
    log_file="logs/build_price_distributions.log",
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
        / f"price_distribution_{INTERVAL}"
        / symbol
        / f"price_distribution_{INTERVAL}_{symbol}_{date_part}.parquet"
    )


def build_distribution_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    date_part: str,
    output_path: Path,
) -> None:
    """
    Build and save a price distribution for one symbol.

    Trades are read sequentially in exchange trade ID order and aggregated in
    one pass. Seconds without trades do not produce distribution rows.

    Parameters:
        conn (sqlite3.Connection): Open SQLite database connection.
        symbol (str): Trading pair symbol.
        date_part (str): Date part from the raw database filename.
        output_path (Path): Target Parquet output path.
    """
    logger.info(
        "Building price distribution interval=%s symbol=%s date=%s output=%s",
        INTERVAL,
        symbol,
        date_part,
        output_path,
    )

    query = """
        SELECT
            trade_time,
            exchange_trade_id,
            price,
            quantity,
            is_buyer_maker
        FROM trades
        WHERE symbol = ?
        ORDER BY exchange_trade_id;
    """

    cursor = conn.execute(query, (symbol,))

    distribution_rows = []

    current_bucket = None
    current_distribution = {}

    while rows := cursor.fetchmany(FETCH_SIZE):
        for (
            trade_time,
            _exchange_trade_id,
            price,
            quantity,
            is_buyer_maker,
        ) in rows:
            bucket_time = (trade_time // INTERVAL_MS) * INTERVAL_MS

            if current_bucket is None:
                current_bucket = bucket_time

            if bucket_time < current_bucket:
                raise ValueError(
                    "Trade time moved backwards "
                    f"symbol={symbol} "
                    f"current_bucket={current_bucket} "
                    f"trade_bucket={bucket_time}"
                )

            if bucket_time > current_bucket:
                for price_bucket in sorted(current_distribution):
                    buy_volume, sell_volume = current_distribution[price_bucket]

                    distribution_rows.append(
                        (
                            current_bucket,
                            price_bucket,
                            buy_volume,
                            sell_volume,
                        )
                    )

                current_bucket = bucket_time
                current_distribution = {}

            price_bucket = int(price / PRICE_BUCKET_SIZE) * PRICE_BUCKET_SIZE

            if price_bucket not in current_distribution:
                current_distribution[price_bucket] = [0.0, 0.0]

            if is_buyer_maker == 0:
                current_distribution[price_bucket][0] += quantity
            else:
                current_distribution[price_bucket][1] += quantity

    if current_bucket is not None:
        for price_bucket in sorted(current_distribution):
            buy_volume, sell_volume = current_distribution[price_bucket]

            distribution_rows.append(
                (
                    current_bucket,
                    price_bucket,
                    buy_volume,
                    sell_volume,
                )
            )

    if not distribution_rows:
        logger.warning(
            "No price distribution rows interval=%s symbol=%s date=%s",
            INTERVAL,
            symbol,
            date_part,
        )
        return

    df = pd.DataFrame(
        distribution_rows,
        columns=[
            "timestamp",
            "price_bucket",
            "buy_volume",
            "sell_volume",
        ],
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    logger.info(
        "Saved price distribution interval=%s symbol=%s date=%s "
        "rows=%d start=%s end=%s output=%s",
        INTERVAL,
        symbol,
        date_part,
        len(df),
        df["timestamp"].min(),
        df["timestamp"].max(),
        output_path,
    )


def build_distributions_for_file(raw_db_path: Path) -> None:
    """
    Build price distributions for every symbol in one raw database file.

    Parameters:
        raw_db_path (Path): Raw SQLite database path.
    """
    date_part = extract_date_part(raw_db_path)

    logger.info(
        "Processing raw database date=%s path=%s",
        date_part,
        raw_db_path,
    )

    with closing(sqlite3.connect(raw_db_path)) as conn:
        logger.debug(
            "Opened database path=%s",
            raw_db_path,
        )

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
                    "Skipping existing price distribution interval=%s "
                    "symbol=%s date=%s output=%s",
                    INTERVAL,
                    symbol,
                    date_part,
                    output_path,
                )
                continue

            build_distribution_for_symbol(
                conn=conn,
                symbol=symbol,
                date_part=date_part,
                output_path=output_path,
            )


def main() -> None:
    """
    Run the price distribution build pipeline for all raw databases.
    """
    logger.info(
        "Starting price distribution pipeline raw_dir=%s "
        "processed_dir=%s interval=%s price_bucket_size=%s",
        RAW_DIR,
        PROCESSED_DIR,
        INTERVAL,
        PRICE_BUCKET_SIZE,
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
            build_distributions_for_file(raw_db_path)
        except Exception:
            logger.exception(
                "Failed processing raw database path=%s",
                raw_db_path,
            )

    logger.info("Finished price distribution pipeline")


if __name__ == "__main__":
    main()
