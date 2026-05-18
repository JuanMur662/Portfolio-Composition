"""
Configuration constants for the portfolio tracker.

Edit this file to add new ticker mappings, sectors, or benchmarks.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# App identity                                                                #
# --------------------------------------------------------------------------- #
APP_NAME = "Mesa de Trading"
APP_TAGLINE = "Personal Portfolio Terminal"
APP_VERSION = "0.1.0"

# --------------------------------------------------------------------------- #
# Brokers                                                                     #
# --------------------------------------------------------------------------- #
BROKERS = {
    "trii": {
        "name": "Trii",
        "currency": "COP",
        "region": "Colombia / LatAm",
        "benchmark": "ICOL",       # iShares MSCI Colombia ETF (NYSE-listed proxy)
        "benchmark_name": "MSCI Colombia (ICOL)",
        "flag": "🇨🇴",
    },
    "etoro": {
        "name": "eToro",
        "currency": "USD",
        "region": "Global",
        "benchmark": "SPY",        # S&P 500
        "benchmark_name": "S&P 500 (SPY)",
        "flag": "🌎",
    },
}

# --------------------------------------------------------------------------- #
# Ticker resolution                                                            #
# --------------------------------------------------------------------------- #
# Maps user-friendly ticker -> Yahoo Finance ticker.
# If a ticker isn't here, we try it directly on yfinance.
# Add aliases as you discover them.
YFINANCE_ALIASES: dict[str, str] = {
    # US-listed stocks bought through Trii
    "NU":   "NU",            # Nubank (NYSE)
    "IYF":  "IYF",           # iShares U.S. Financials ETF
    "XLF":  "XLF",           # Financial Select Sector SPDR
    "IYG":  "IYG",           # iShares U.S. Financial Services ETF
    "VFH":  "VFH",           # Vanguard Financials

    # BVC tickers — yfinance coverage is patchy; we attempt these formats
    "GEB":      "GEB.CL",    # Grupo Energía Bogotá (try .CL first, fallback to manual)
    "ECOPETROL": "EC",       # Ecopetrol → NYSE ADR
    "BCOLOMBIA": "CIB",      # Bancolombia → NYSE ADR
    "PFBCOLOM":  "CIB",
    "ICOLCAP":   "ICOL",     # COLCAP → use ICOL (iShares MSCI Colombia) as proxy

    # eToro / global benchmarks
    "SPY":  "SPY",
    "QQQ":  "QQQ",
    "ICOL": "ICOL",
}

# Sector and country metadata per ticker for exposure analysis.
# (sector, country, asset_class)
TICKER_METADATA: dict[str, tuple[str, str, str]] = {
    "NU":        ("Financial Services", "Brazil",         "Stock"),
    "GEB":       ("Utilities",          "Colombia",       "Stock"),
    "ECOPETROL": ("Energy",             "Colombia",       "Stock"),
    "BCOLOMBIA": ("Financial Services", "Colombia",       "Stock"),
    "PFBCOLOM":  ("Financial Services", "Colombia",       "Stock"),
    "ICOLCAP":   ("Diversified",        "Colombia",       "ETF"),
    "ICOL":      ("Diversified",        "Colombia",       "ETF"),
    "IYF":       ("Financial Services", "United States",  "ETF"),
    "XLF":       ("Financial Services", "United States",  "ETF"),
    "IYG":       ("Financial Services", "United States",  "ETF"),
    "VFH":       ("Financial Services", "United States",  "ETF"),
    "SPY":       ("Diversified",        "United States",  "ETF"),
    "QQQ":       ("Technology",         "United States",  "ETF"),
}

# Friendly display names
TICKER_NAMES: dict[str, str] = {
    "NU":        "Nubank Holdings",
    "GEB":       "Grupo Energía Bogotá",
    "ECOPETROL": "Ecopetrol",
    "BCOLOMBIA": "Bancolombia",
    "PFBCOLOM":  "Bancolombia (Pref.)",
    "ICOLCAP":   "iShares COLCAP ETF",
    "ICOL":      "iShares MSCI Colombia",
    "IYF":       "iShares U.S. Financials",
    "XLF":       "Financial Select SPDR",
    "IYG":       "iShares U.S. Financial Services",
    "VFH":       "Vanguard Financials",
    "SPY":       "SPDR S&P 500",
    "QQQ":       "Invesco QQQ Trust",
}

# --------------------------------------------------------------------------- #
# UI                                                                          #
# --------------------------------------------------------------------------- #
# Color palette — deep dark, single warm accent (refined, not Bloomberg-loud)
COLORS = {
    "bg":              "#0a0e14",
    "bg_elevated":     "#11161d",
    "bg_card":         "#151b24",
    "border":          "#1f2731",
    "border_strong":   "#2a3441",
    "text":            "#d6deeb",
    "text_muted":      "#6b7a8f",
    "text_subtle":     "#4a5566",
    "accent":          "#d97706",   # amber-600
    "accent_dim":      "#92400e",
    "accent_glow":     "rgba(217, 119, 6, 0.15)",
    "secondary":       "#06b6d4",   # cyan-500
    "positive":        "#10b981",   # emerald
    "negative":        "#ef4444",   # red-500
    "neutral":         "#6b7a8f",
}

# Caching durations (seconds)
PRICE_CACHE_TTL = 60 * 15   # 15 minutes
FX_CACHE_TTL    = 60 * 60   # 1 hour
