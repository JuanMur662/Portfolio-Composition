"""
Portfolio analytics.

Single source of truth: transactions table.
Everything else (positions, P&L, returns) is derived from it.

Cost basis method: weighted average (matches how brokers usually report).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import numpy as np
import pandas as pd

import db, prices
from config import TICKER_METADATA, TICKER_NAMES, BROKERS


# --------------------------------------------------------------------------- #
# Position aggregation                                                        #
# --------------------------------------------------------------------------- #
@dataclass
class Position:
    broker: str
    ticker: str
    name: str
    quantity: float
    avg_cost: float          # weighted-average purchase price
    cost_basis: float        # total $ invested currently held (qty * avg_cost)
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_pct: float
    currency: str
    price_source: str        # 'yfinance' | 'manual' | 'unavailable'
    sector: str
    country: str
    asset_class: str
    realized_pl: float       # from prior partial sales of this ticker
    last_action_date: date
    commissions_total: float


def _compute_running_position(tx_ticker: pd.DataFrame) -> dict:
    """Walk a single ticker's transactions chronologically.

    Returns running state: current qty, avg cost, realized P&L, total commissions.
    Weighted-average cost basis (commissions added to cost on buys,
    netted against proceeds on sells).
    """
    qty = 0.0
    avg_cost = 0.0
    realized = 0.0
    commissions = 0.0
    for _, row in tx_ticker.sort_values("trade_date").iterrows():
        c = float(row["commission"] or 0)
        commissions += c
        if row["action"] == "buy":
            new_qty = qty + row["quantity"]
            # Commission rolls into cost basis
            total_cost = (qty * avg_cost) + (row["quantity"] * row["price"]) + c
            avg_cost = total_cost / new_qty if new_qty else 0.0
            qty = new_qty
        else:  # sell
            sell_qty = row["quantity"]
            proceeds = sell_qty * row["price"] - c
            cost_of_sold = sell_qty * avg_cost
            realized += proceeds - cost_of_sold
            qty -= sell_qty
            if qty <= 1e-9:
                qty = 0.0
                avg_cost = 0.0
    return {
        "quantity": qty,
        "avg_cost": avg_cost,
        "realized_pl": realized,
        "commissions": commissions,
    }


def compute_positions(broker: str | None = None) -> list[Position]:
    """Build the live position list for a broker (or all)."""
    txs = db.get_transactions(broker=broker)
    if txs.empty:
        return []

    positions: list[Position] = []
    for (b, t), grp in txs.groupby(["broker", "ticker"]):
        state = _compute_running_position(grp)
        currency = grp["currency"].iloc[-1]
        last_action = grp["trade_date"].max()
        if isinstance(last_action, pd.Timestamp):
            last_action = last_action.date()

        meta = TICKER_METADATA.get(t, ("Other", "Unknown", "Other"))
        sector, country, asset_class = meta
        name = TICKER_NAMES.get(t, t)

        # Get current price (only matters if we still hold)
        quote = prices.get_price(t, default_currency=currency) if state["quantity"] > 0 else None
        current_price = quote.price if quote else 0.0
        price_source = quote.source if quote else "unavailable"

        market_value = state["quantity"] * current_price
        unrealized = (current_price - state["avg_cost"]) * state["quantity"]
        unrealized_pct = (
            (current_price / state["avg_cost"] - 1) * 100
            if state["avg_cost"] > 0 else 0.0
        )

        positions.append(Position(
            broker=b,
            ticker=t,
            name=name,
            quantity=state["quantity"],
            avg_cost=state["avg_cost"],
            cost_basis=state["quantity"] * state["avg_cost"],
            current_price=current_price,
            market_value=market_value,
            unrealized_pl=unrealized,
            unrealized_pl_pct=unrealized_pct,
            currency=currency,
            price_source=price_source,
            sector=sector,
            country=country,
            asset_class=asset_class,
            realized_pl=state["realized_pl"],
            last_action_date=last_action,
            commissions_total=state["commissions"],
        ))
    return positions


def positions_dataframe(broker: str | None = None,
                        only_open: bool = True) -> pd.DataFrame:
    pos = compute_positions(broker)
    if only_open:
        pos = [p for p in pos if p.quantity > 0]
    if not pos:
        return pd.DataFrame()
    return pd.DataFrame([p.__dict__ for p in pos])


# --------------------------------------------------------------------------- #
# Closed positions (history)                                                  #
# --------------------------------------------------------------------------- #
def closed_positions(broker: str | None = None) -> pd.DataFrame:
    """Reconstruct closed trade-pairs using FIFO matching of buys against sells.

    Each row: a sell event matched to its earliest buy lot, producing realized P&L.
    """
    txs = db.get_transactions(broker=broker)
    if txs.empty:
        return pd.DataFrame()

    rows = []
    for (b, t), grp in txs.groupby(["broker", "ticker"]):
        buys: list[dict] = []  # FIFO queue of {qty, price, date, commission_per_share}
        for _, r in grp.sort_values("trade_date").iterrows():
            c_per_share = (r["commission"] or 0) / r["quantity"] if r["quantity"] else 0
            if r["action"] == "buy":
                buys.append({
                    "qty_remaining": r["quantity"],
                    "price": r["price"],
                    "date": r["trade_date"],
                    "c_per_share": c_per_share,
                })
            else:  # sell
                qty_to_sell = r["quantity"]
                sell_c_per_share = c_per_share
                while qty_to_sell > 1e-9 and buys:
                    lot = buys[0]
                    use = min(lot["qty_remaining"], qty_to_sell)
                    realized = use * (r["price"] - lot["price"])
                    realized -= use * (lot["c_per_share"] + sell_c_per_share)
                    rows.append({
                        "broker":      b,
                        "ticker":      t,
                        "name":        TICKER_NAMES.get(t, t),
                        "quantity":    use,
                        "buy_price":   lot["price"],
                        "buy_date":    lot["date"],
                        "sell_price":  r["price"],
                        "sell_date":   r["trade_date"],
                        "currency":    r["currency"],
                        "realized_pl": realized,
                        "return_pct":  (r["price"] / lot["price"] - 1) * 100,
                        "holding_days": (
                            pd.to_datetime(r["trade_date"]) - pd.to_datetime(lot["date"])
                        ).days,
                    })
                    lot["qty_remaining"] -= use
                    qty_to_sell -= use
                    if lot["qty_remaining"] <= 1e-9:
                        buys.pop(0)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Aggregate metrics                                                           #
# --------------------------------------------------------------------------- #
@dataclass
class PortfolioStats:
    broker: str
    currency: str
    n_positions: int
    cost_basis: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_pct: float
    realized_pl: float
    dividends: float
    total_pl: float           # unrealized + realized + dividends
    total_pl_pct: float       # vs total capital deployed
    commissions: float
    best: tuple[str, float] | None
    worst: tuple[str, float] | None


def portfolio_stats(broker: str) -> PortfolioStats:
    positions = compute_positions(broker)
    open_pos = [p for p in positions if p.quantity > 0]
    all_pos = positions  # includes closed (qty=0) — they still contribute realized P&L

    cost_basis    = sum(p.cost_basis for p in open_pos)
    market_value  = sum(p.market_value for p in open_pos)
    unrealized    = sum(p.unrealized_pl for p in open_pos)
    realized      = sum(p.realized_pl for p in all_pos)

    div_df = db.get_dividends(broker)
    dividends = float(div_df["amount"].sum()) if not div_df.empty else 0.0

    total_pl = unrealized + realized + dividends
    # Capital deployed = cumulative net cash out (buys - sells*price), simpler proxy:
    txs = db.get_transactions(broker)
    if not txs.empty:
        deployed = float(
            ((txs["quantity"] * txs["price"] + txs["commission"])
             * np.where(txs["action"] == "buy", 1, 0)).sum()
        )
    else:
        deployed = 0.0
    pct = (total_pl / deployed * 100) if deployed > 0 else 0.0

    commissions = sum(p.commissions_total for p in all_pos)

    best = worst = None
    if open_pos:
        best_p = max(open_pos, key=lambda p: p.unrealized_pl_pct)
        worst_p = min(open_pos, key=lambda p: p.unrealized_pl_pct)
        best = (best_p.ticker, best_p.unrealized_pl_pct)
        worst = (worst_p.ticker, worst_p.unrealized_pl_pct)

    return PortfolioStats(
        broker=broker,
        currency=BROKERS[broker]["currency"],
        n_positions=len(open_pos),
        cost_basis=cost_basis,
        market_value=market_value,
        unrealized_pl=unrealized,
        unrealized_pl_pct=(unrealized / cost_basis * 100) if cost_basis > 0 else 0.0,
        realized_pl=realized,
        dividends=dividends,
        total_pl=total_pl,
        total_pl_pct=pct,
        commissions=commissions,
        best=best,
        worst=worst,
    )


# --------------------------------------------------------------------------- #
# IRR / TWR                                                                   #
# --------------------------------------------------------------------------- #
def _xirr(cashflows: list[tuple[date, float]],
          guess: float = 0.1, max_iter: int = 100) -> float | None:
    """Compute XIRR (annualized) via Newton-Raphson.

    cashflows: [(date, amount)] — negative = invested, positive = received.
    """
    if not cashflows or len(cashflows) < 2:
        return None
    cashflows = sorted(cashflows, key=lambda x: x[0])
    t0 = cashflows[0][0]
    days = np.array([(d - t0).days for d, _ in cashflows], dtype=float)
    amts = np.array([a for _, a in cashflows], dtype=float)

    if (amts > 0).all() or (amts < 0).all():
        return None  # all same sign → no IRR

    r = guess
    for _ in range(max_iter):
        denom = (1 + r) ** (days / 365.0)
        f = np.sum(amts / denom)
        df = np.sum(-days / 365.0 * amts / (denom * (1 + r)))
        if abs(df) < 1e-12:
            break
        r_new = r - f / df
        if abs(r_new - r) < 1e-7:
            return r_new
        r = max(r_new, -0.9999)
    return r


def portfolio_irr(broker: str, as_of: date | None = None) -> float | None:
    """XIRR for the broker — annualized return accounting for timing of cashflows."""
    txs = db.get_transactions(broker)
    if txs.empty:
        return None
    cashflows: list[tuple[date, float]] = []
    for _, r in txs.iterrows():
        d = r["trade_date"].date() if hasattr(r["trade_date"], "date") else r["trade_date"]
        net = r["quantity"] * r["price"] + (r["commission"] or 0)
        cashflows.append((d, -net if r["action"] == "buy" else net))

    divs = db.get_dividends(broker)
    for _, r in divs.iterrows():
        d = r["pay_date"].date() if hasattr(r["pay_date"], "date") else r["pay_date"]
        cashflows.append((d, float(r["amount"])))

    # Add a terminal cashflow = current market value
    stats = portfolio_stats(broker)
    cashflows.append((as_of or date.today(), stats.market_value))

    return _xirr(cashflows)


# --------------------------------------------------------------------------- #
# Exposure breakdowns                                                          #
# --------------------------------------------------------------------------- #
def exposure_by(field: str, broker: str | None = None) -> pd.DataFrame:
    """Aggregate market value by `field` (sector | country | asset_class | ticker)."""
    df = positions_dataframe(broker, only_open=True)
    if df.empty:
        return pd.DataFrame(columns=[field, "market_value", "weight"])
    agg = df.groupby(field, as_index=False)["market_value"].sum()
    agg = agg.sort_values("market_value", ascending=False)
    total = agg["market_value"].sum()
    agg["weight"] = (agg["market_value"] / total * 100) if total > 0 else 0
    return agg


# --------------------------------------------------------------------------- #
# Benchmark comparison                                                        #
# --------------------------------------------------------------------------- #
def benchmark_series(broker: str, lookback_days: int = 365) -> pd.DataFrame:
    """Return % cumulative return series for portfolio vs benchmark since first trade.

    Portfolio series is computed as the time-weighted value of held positions
    using historical prices. Approximation: assume positions held from purchase
    date forward at their actual quantities (ignores intermediate sales).
    """
    bench_ticker = BROKERS[broker]["benchmark"]
    bench = prices.get_history(bench_ticker, period="1y")
    if bench.empty:
        return pd.DataFrame()

    txs = db.get_transactions(broker)
    if txs.empty:
        return pd.DataFrame()

    first_date = txs["trade_date"].min()
    if isinstance(first_date, pd.Timestamp):
        first_date = first_date.tz_localize(None) if first_date.tz else first_date

    bench = bench[bench.index >= first_date].copy()
    if bench.empty:
        return pd.DataFrame()
    bench["bench_ret"] = (bench["Close"] / bench["Close"].iloc[0] - 1) * 100

    # Portfolio value series
    open_tickers = txs["ticker"].unique().tolist()
    histories: dict[str, pd.DataFrame] = {}
    for t in open_tickers:
        h = prices.get_history(t, period="1y")
        if not h.empty:
            histories[t] = h["Close"]

    if not histories:
        return pd.DataFrame()

    # For each day, sum quantity-held * price
    all_dates = bench.index
    pf_values = []
    for d in all_dates:
        v = 0.0
        for t in open_tickers:
            held = txs[(txs["ticker"] == t) & (txs["trade_date"] <= d)]
            if held.empty:
                continue
            qty = (
                held[held["action"] == "buy"]["quantity"].sum()
                - held[held["action"] == "sell"]["quantity"].sum()
            )
            if qty <= 0 or t not in histories:
                continue
            # nearest historical price ≤ d
            series = histories[t]
            valid = series[series.index <= d]
            if valid.empty:
                continue
            v += qty * valid.iloc[-1]
        pf_values.append(v)

    df = pd.DataFrame({"date": all_dates, "portfolio_value": pf_values,
                       "benchmark_pct": bench["bench_ret"].values})
    df = df[df["portfolio_value"] > 0].reset_index(drop=True)
    if df.empty:
        return df
    df["portfolio_pct"] = (df["portfolio_value"] / df["portfolio_value"].iloc[0] - 1) * 100
    return df
