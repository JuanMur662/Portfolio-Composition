"""
Optional helper: seeds the database with your current open positions.

Usage:
    python seed_positions.py

Safe to re-run; checks for duplicates by (broker, ticker, date, qty, price).
Edit the POSITIONS list below if your initial holdings differ.
"""
from datetime import date
import db

POSITIONS = [
    # broker, ticker,  qty, price (per share), currency, trade_date, commission
    ("trii", "NU",       40,  48_500,  "COP", date(2026, 5, 11), 0),
    ("trii", "GEB",     283,   2_994,  "COP", date(2026, 5, 11), 0),
    # NOTE: confirm the exact iShares ETF ticker — IYF is a placeholder
    ("trii", "IYF",       5,  61_020,  "COP", date(2026, 5, 11), 0),
]


def main() -> None:
    db.init_db()
    existing = db.get_transactions()
    seeded = 0
    for broker, ticker, qty, price, ccy, d, comm in POSITIONS:
        match = existing[
            (existing["broker"] == broker) &
            (existing["ticker"] == ticker) &
            (existing["quantity"] == qty) &
            (existing["price"] == price)
        ]
        if not match.empty:
            print(f"  skip   {ticker:10s}  (already present)")
            continue
        db.add_transaction(db.Transaction(
            broker=broker, ticker=ticker, action="buy",
            quantity=qty, price=price, currency=ccy,
            commission=comm, order_type="market", trade_date=d,
            notes="Initial seed",
        ))
        print(f"  added  {ticker:10s}  {qty} @ {price:,} {ccy}")
        seeded += 1
    print(f"\n✓ Seeded {seeded} position(s). Run `streamlit run app.py` to view.")


if __name__ == "__main__":
    main()
