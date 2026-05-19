import sqlite3
import json
from pathlib import Path

def connect_db(database_path: str) -> sqlite3.Connection:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(database_path)
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

    return conn

def insert_trade(conn: sqlite3.Connection, msg:dict) -> None:
    
    conn.execute("""
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
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    msg["e"],
                    msg["E"],
                    msg["T"],
                    msg["s"],
                    msg["t"],
                    float(msg["p"]),
                    float(msg["q"]),
                    int(msg["m"]),
                    json.dumps(msg)
                ),
    )
    conn.commit()
