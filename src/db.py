import sqlite3
import json
from pathlib import Path
from datetime import datetime, UTC

def daily_database_path(database_dir: str) -> str:
    date_str = datetime.now(UTC).strftime("%Y_%m_%d")
    return str(Path(database_dir) / f"trades_{date_str}.sqlite")

def connect_db(database_path: str) -> sqlite3.Connection:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(database_path, timeout=30)

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("""                      
                CREATE TABLE IF NOT EXISTS trades (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                            
                    event_type TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    trade_time INTEGER NOT NULL,            

                    exchange_trade_id INTEGER NOT NULL,

                    
                    symbol TEXT NOT NULL,

                    price REAL NOT NULL,
                    quantity REAL NOT NULL,

                    is_buyer_maker INTEGER NOT NULL,

                    raw_json TEXT NOT NULL,
                                
                    UNIQUE(symbol, exchange_trade_id)
                );
    """)

    conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_time
                ON trades(symbol, trade_time)
    """)

    conn.commit()

    return conn

def insert_trades(conn: sqlite3.Connection, messages: list[dict]) -> None:
    rows = [
        (
            msg["e"],
            msg["E"],
            msg["T"],
            msg["s"],
            msg["t"],
            float(msg["p"]),
            float(msg["q"]),
            int(msg["m"]),
            json.dumps(msg),
        )
        for msg in messages
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO trades (
            event_type,
            event_time,
            trade_time,
            symbol,
            exchange_trade_id,
            price,
            quantity,
            is_buyer_maker,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()