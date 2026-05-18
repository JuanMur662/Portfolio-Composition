"""
SQLite persistence layer.

Stores transactions and dividends. All position aggregation happens in `metrics.py`
from the raw transaction log — single source of truth.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"


# --------------------------------------------------------------------------- #
# Connection                                                                  #
# --------------------------------------------------------------------------- #
@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                broker       TEXT    NOT NULL CHECK(broker IN ('trii','etoro')),
                ticker       TEXT    NOT NULL,
                action       TEXT    NOT NULL CHECK(action IN ('buy','sell')),
                quantity     REAL    NOT NULL CHECK(quantity > 0),
                price        REAL    NOT NULL CHECK(price > 0),
                currency     TEXT    NOT NULL,
                commission   REAL    NOT NULL DEFAULT 0,
                order_type   TEXT    NOT NULL DEFAULT 'market'
                                CHECK(order_type IN ('market','limit')),
                trade_date   TEXT    NOT NULL,
                notes        TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_tx_broker_ticker
                ON transactions(broker, ticker);
            CREATE INDEX IF NOT EXISTS idx_tx_date
                ON transactions(trade_date);

            CREATE TABLE IF NOT EXISTS dividends (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                broker       TEXT    NOT NULL CHECK(broker IN ('trii','etoro')),
                ticker       TEXT    NOT NULL,
                amount       REAL    NOT NULL CHECK(amount > 0),
                currency     TEXT    NOT NULL,
                pay_date     TEXT    NOT NULL,
                notes        TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS manual_prices (
                ticker       TEXT    PRIMARY KEY,
                price        REAL    NOT NULL,
                currency     TEXT    NOT NULL,
                updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


# --------------------------------------------------------------------------- #
# Transactions                                                                #
# --------------------------------------------------------------------------- #
@dataclass
class Transaction:
    broker: str
    ticker: str
    action: str          # 'buy' or 'sell'
    quantity: float
    price: float
    currency: str
    trade_date: date
    commission: float = 0.0
    order_type: str = "market"
    notes: str | None = None
    id: int | None = None


def add_transaction(tx: Transaction) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO transactions
              (broker, ticker, action, quantity, price, currency,
               commission, order_type, trade_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx.broker,
                tx.ticker.upper().strip(),
                tx.action,
                tx.quantity,
                tx.price,
                tx.currency,
                tx.commission,
                tx.order_type,
                tx.trade_date.isoformat() if isinstance(tx.trade_date, date)
                    else str(tx.trade_date),
                tx.notes,
            ),
        )
        return cur.lastrowid


def delete_transaction(tx_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))


def update_transaction(tx_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE transactions SET {cols} WHERE id = ?",
            (*fields.values(), tx_id),
        )


def get_transactions(broker: Optional[str] = None) -> pd.DataFrame:
    """Return all transactions, optionally filtered by broker."""
    query = "SELECT * FROM transactions"
    params: tuple = ()
    if broker:
        query += " WHERE broker = ?"
        params = (broker,)
    query += " ORDER BY trade_date ASC, id ASC"
    with get_conn() as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["trade_date"])
    return df


# --------------------------------------------------------------------------- #
# Dividends                                                                   #
# --------------------------------------------------------------------------- #
@dataclass
class Dividend:
    broker: str
    ticker: str
    amount: float
    currency: str
    pay_date: date
    notes: str | None = None


def add_dividend(div: Dividend) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO dividends
              (broker, ticker, amount, currency, pay_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                div.broker,
                div.ticker.upper().strip(),
                div.amount,
                div.currency,
                div.pay_date.isoformat() if isinstance(div.pay_date, date)
                    else str(div.pay_date),
                div.notes,
            ),
        )
        return cur.lastrowid


def get_dividends(broker: Optional[str] = None) -> pd.DataFrame:
    query = "SELECT * FROM dividends"
    params: tuple = ()
    if broker:
        query += " WHERE broker = ?"
        params = (broker,)
    query += " ORDER BY pay_date DESC"
    with get_conn() as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["pay_date"])
    return df


def delete_dividend(div_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM dividends WHERE id = ?", (div_id,))


# --------------------------------------------------------------------------- #
# Manual price overrides                                                      #
# --------------------------------------------------------------------------- #
def set_manual_price(ticker: str, price: float, currency: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO manual_prices (ticker, price, currency, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(ticker) DO UPDATE SET
              price = excluded.price,
              currency = excluded.currency,
              updated_at = excluded.updated_at
            """,
            (ticker.upper().strip(), price, currency),
        )


def get_manual_price(ticker: str) -> tuple[float, str, str] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT price, currency, updated_at FROM manual_prices WHERE ticker = ?",
            (ticker.upper().strip(),),
        ).fetchone()
    return (row["price"], row["currency"], row["updated_at"]) if row else None


def all_manual_prices() -> dict[str, dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM manual_prices").fetchall()
    return {r["ticker"]: dict(r) for r in rows}


# --------------------------------------------------------------------------- #
# Export                                                                       #
# --------------------------------------------------------------------------- #
def export_all() -> dict[str, pd.DataFrame]:
    """Return all tables for export to Excel / CSV."""
    return {
        "transactions": get_transactions(),
        "dividends":    get_dividends(),
        "manual_prices": pd.DataFrame(all_manual_prices().values()),
    }
