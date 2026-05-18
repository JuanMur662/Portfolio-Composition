"""
Price fetching layer.

Strategy:
 1. Look for a manual override (set in Settings page).
 2. Try yfinance with the alias from config, then the raw ticker.
 3. Return None if everything fails — UI shows "manual entry needed".

All look-ups are cached for PRICE_CACHE_TTL seconds via Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from core.config import YFINANCE_ALIASES, PRICE_CACHE_TTL, FX_CACHE_TTL
from core import db


@dataclass
class PriceQuote:
    ticker: str
    price: float
    currency: str
    source: str           # 'yfinance' | 'manual' | 'unavailable'
    as_of: str            # ISO datetime string
    pct_change_1d: Optional[float] = None


# --------------------------------------------------------------------------- #
# yfinance lookups                                                            #
# --------------------------------------------------------------------------- #
def _yf_quote(yf_ticker: str) -> dict | None:
    """Single yfinance lookup. Returns None on any failure."""
    try:
        import yfinance as yf
        tk = yf.Ticker(yf_ticker)
        fi = tk.fast_info
        price = (
            getattr(fi, "last_price", None)
            or fi.get("lastPrice") if hasattr(fi, "get") else None
        )
        if price is None:
            return None
        prev = (
            getattr(fi, "previous_close", None)
            or (fi.get("previousClose") if hasattr(fi, "get") else None)
        )
        currency = (
            getattr(fi, "currency", None)
            or (fi.get("currency") if hasattr(fi, "get") else None)
            or "USD"
        )
        pct = ((price - prev) / prev * 100) if prev else None
        return {
            "price": float(price),
            "currency": currency.upper(),
            "pct_change_1d": pct,
        }
    except Exception:
        return None


@st.cache_data(ttl=PRICE_CACHE_TTL, show_spinner=False)
def get_price(ticker: str, default_currency: str = "USD") -> PriceQuote:
    """Resolve current price for a ticker with fallbacks."""
    t = ticker.upper().strip()

    # 1. Manual override
    manual = db.get_manual_price(t)
    if manual:
        price, currency, updated = manual
        return PriceQuote(
            ticker=t, price=price, currency=currency,
            source="manual", as_of=updated,
        )

    # 2. yfinance with alias, then raw
    candidates = []
    if t in YFINANCE_ALIASES:
        candidates.append(YFINANCE_ALIASES[t])
    if t not in candidates:
        candidates.append(t)

    for yt in candidates:
        result = _yf_quote(yt)
        if result:
            return PriceQuote(
                ticker=t,
                price=result["price"],
                currency=result["currency"],
                source="yfinance",
                as_of=datetime.now().isoformat(timespec="seconds"),
                pct_change_1d=result.get("pct_change_1d"),
            )

    # 3. Unavailable
    return PriceQuote(
        ticker=t, price=0.0, currency=default_currency,
        source="unavailable", as_of=datetime.now().isoformat(timespec="seconds"),
    )


@st.cache_data(ttl=PRICE_CACHE_TTL, show_spinner=False)
def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Historical OHLC for charting and TWR computation."""
    yf_ticker = YFINANCE_ALIASES.get(ticker.upper().strip(), ticker)
    try:
        import yfinance as yf
        df = yf.Ticker(yf_ticker).history(period=period, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


# --------------------------------------------------------------------------- #
# FX                                                                          #
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=FX_CACHE_TTL, show_spinner=False)
def get_fx_rate(from_ccy: str, to_ccy: str) -> float:
    """Spot FX. Returns 1.0 if same currency or if lookup fails."""
    if from_ccy == to_ccy:
        return 1.0
    pair = f"{from_ccy}{to_ccy}=X"
    try:
        import yfinance as yf
        tk = yf.Ticker(pair)
        fi = tk.fast_info
        rate = (
            getattr(fi, "last_price", None)
            or (fi.get("lastPrice") if hasattr(fi, "get") else None)
        )
        return float(rate) if rate else 1.0
    except Exception:
        return 1.0


# --------------------------------------------------------------------------- #
# Bulk helpers                                                                #
# --------------------------------------------------------------------------- #
def get_prices_for(tickers: list[str], default_currency: str = "USD") -> dict[str, PriceQuote]:
    return {t: get_price(t, default_currency) for t in tickers}
