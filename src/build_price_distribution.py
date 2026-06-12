from pathlib import Path
import sqlite3

import pandas as pd

from config.settings import RAW_DIR, PROCESSED_DIR
from config.logging_setup import setup_logger


INTERVAL = "15s"
INTERVAL_MS = 15_000
PRICE_BUCKET_SIZE = 1


logger = setup_logger(
    name="build_price_distributions",
    log_file="logs/build_price_distributions.log",
)


def extract_date_part(raw_db_path: Path) -> str:
    return raw_db_path.stem.replace("trades_", "")


def get_symbols(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("""
        SELECT DISTINCT symbol
        FROM trades
        ORDER BY symbol;
    """).fetchall()

    return [row[0] for row in rows]


def output_path_for(symbol: str, date_part: str) -> Path:
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
    logger.info(
        "Building price distribution interval=%s symbol=%s date=%s output=%s",
        INTERVAL,
        symbol,
        date_part,
        output_path,
    )

    query = f"""
    WITH bucketed AS (
        SELECT
            (trade_time / {INTERVAL_MS}) * {INTERVAL_MS} AS bucket_time,
            CAST(price / {PRICE_BUCKET_SIZE} AS INTEGER) * {PRICE_BUCKET_SIZE} AS price_bucket,
            quantity,
            is_buyer_maker
        FROM trades
        WHERE symbol = ?
    )
    SELECT
        datetime(bucket_time / 1000, 'unixepoch') AS timestamp,
        price_bucket,

        SUM(
            CASE
                WHEN is_buyer_maker = 0
                THEN quantity
                ELSE 0
            END
        ) AS buy_volume,

        SUM(
            CASE
                WHEN is_buyer_maker = 1
                THEN quantity
                ELSE 0
            END
        ) AS sell_volume

    FROM bucketed
    GROUP BY
        bucket_time,
        price_bucket
    ORDER BY
        bucket_time,
        price_bucket;
    """

    df = pd.read_sql_query(query, conn, params=(symbol,))

    if df.empty:
        logger.warning(
            "No price distribution rows interval=%s symbol=%s date=%s",
            INTERVAL,
            symbol,
            date_part,
        )
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    logger.info(
        "Saved price distribution interval=%s symbol=%s date=%s rows=%d start=%s end=%s output=%s",
        INTERVAL,
        symbol,
        date_part,
        len(df),
        df["timestamp"].min(),
        df["timestamp"].max(),
        output_path,
    )


def build_distributions_for_file(raw_db_path: Path) -> None:
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
                    "Skipping existing price distribution interval=%s symbol=%s date=%s output=%s",
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
    logger.info(
        "Starting price distribution pipeline raw_dir=%s processed_dir=%s interval=%s price_bucket_size=%s",
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