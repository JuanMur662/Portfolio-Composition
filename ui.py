"""
UI styling and shared visual components.

Heavy CSS injection to override default Streamlit appearance and get a
terminal/trading-desk look.
"""
from __future__ import annotations

import streamlit as st
from config import COLORS, APP_NAME, APP_TAGLINE


# --------------------------------------------------------------------------- #
# Global CSS                                                                  #
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700;800&display=swap');

        /* ===== Layout reset ===== */
        .stApp {{
            background: {COLORS["bg"]};
            font-family: 'Manrope', system-ui, sans-serif;
            color: {COLORS["text"]};
        }}
        .main .block-container {{
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1400px;
        }}
        #MainMenu, footer, header {{ visibility: hidden; }}
        .stDeployButton {{ display: none; }}

        /* ===== Typography ===== */
        h1, h2, h3, h4 {{
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: {COLORS["text"]};
        }}
        h1 {{ font-size: 2.25rem; }}
        h2 {{ font-size: 1.5rem; margin-top: 1.5rem; }}
        h3 {{ font-size: 1.15rem; color: {COLORS["text"]}; }}

        .mono {{ font-family: 'JetBrains Mono', monospace; }}
        .muted {{ color: {COLORS["text_muted"]}; }}
        .subtle {{ color: {COLORS["text_subtle"]}; }}

        /* ===== Sidebar ===== */
        [data-testid="stSidebar"] {{
            background: {COLORS["bg_elevated"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        [data-testid="stSidebar"] * {{
            color: {COLORS["text"]} !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            font-family: 'Manrope', sans-serif;
            font-weight: 500;
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            transition: background 0.15s;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background: {COLORS["bg_card"]};
        }}

        /* ===== Buttons ===== */
        .stButton > button {{
            background: {COLORS["bg_card"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border_strong"]};
            border-radius: 6px;
            font-family: 'Manrope', sans-serif;
            font-weight: 500;
            padding: 0.5rem 1.25rem;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            border-color: {COLORS["accent"]};
            color: {COLORS["accent"]};
            background: {COLORS["bg_card"]};
        }}
        .stButton > button[kind="primary"] {{
            background: {COLORS["accent"]};
            border-color: {COLORS["accent"]};
            color: #fff;
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {COLORS["accent_dim"]};
            border-color: {COLORS["accent_dim"]};
            color: #fff;
        }}

        /* ===== Inputs ===== */
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div {{
            background: {COLORS["bg_card"]} !important;
            color: {COLORS["text"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}
        .stTextInput label, .stNumberInput label, .stDateInput label,
        .stSelectbox label, .stRadio label, .stTextArea label {{
            color: {COLORS["text_muted"]} !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}

        /* ===== Cards / metrics ===== */
        .metric-card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            transition: border-color 0.2s;
        }}
        .metric-card:hover {{
            border-color: {COLORS["border_strong"]};
        }}
        .metric-label {{
            color: {COLORS["text_muted"]};
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}
        .metric-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.75rem;
            font-weight: 600;
            color: {COLORS["text"]};
            line-height: 1.2;
        }}
        .metric-delta {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-top: 0.35rem;
        }}
        .pos {{ color: {COLORS["positive"]}; }}
        .neg {{ color: {COLORS["negative"]}; }}

        /* ===== Tables ===== */
        .stDataFrame {{
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
        }}

        /* ===== Tabs ===== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: transparent;
            border-bottom: 1px solid {COLORS["border"]};
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent !important;
            color: {COLORS["text_muted"]} !important;
            border: none !important;
            padding: 0.75rem 1.25rem;
            font-weight: 500;
            font-family: 'Manrope', sans-serif;
        }}
        .stTabs [aria-selected="true"] {{
            color: {COLORS["accent"]} !important;
            border-bottom: 2px solid {COLORS["accent"]} !important;
        }}

        /* ===== Header banner ===== */
        .app-header {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            padding: 0 0 1.5rem 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid {COLORS["border"]};
        }}
        .app-brand {{
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
        }}
        .app-brand .logo {{
            font-family: 'JetBrains Mono', monospace;
            color: {COLORS["accent"]};
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: 0.15em;
        }}
        .app-brand .title {{
            font-size: 1.4rem;
            font-weight: 700;
            color: {COLORS["text"]};
            letter-spacing: -0.02em;
        }}
        .app-brand .tagline {{
            color: {COLORS["text_muted"]};
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        .timestamp {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: {COLORS["text_muted"]};
            letter-spacing: 0.05em;
        }}

        /* ===== Section divider ===== */
        .section-title {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 600;
            color: {COLORS["accent"]};
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid {COLORS["border"]};
        }}

        /* ===== Pills / badges ===== */
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            font-weight: 500;
            letter-spacing: 0.05em;
        }}
        .badge-pos {{ background: rgba(16, 185, 129, 0.15); color: {COLORS["positive"]}; }}
        .badge-neg {{ background: rgba(239, 68, 68, 0.15); color: {COLORS["negative"]}; }}
        .badge-neutral {{ background: {COLORS["bg_card"]}; color: {COLORS["text_muted"]}; }}
        .badge-warn {{ background: rgba(217, 119, 6, 0.15); color: {COLORS["accent"]}; }}

        /* ===== Expander ===== */
        .streamlit-expanderHeader {{
            background: {COLORS["bg_card"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 6px !important;
        }}

        /* ===== Plotly background fix ===== */
        .js-plotly-plot .plotly .modebar {{
            background: transparent !important;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Header banner                                                               #
# --------------------------------------------------------------------------- #
def render_header(subtitle: str | None = None) -> None:
    from datetime import datetime
    now = datetime.now().strftime("%a %d %b %Y · %H:%M:%S")
    st.markdown(
        f"""
        <div class="app-header">
          <div class="app-brand">
            <span class="logo">◐ MESA</span>
            <span class="title">{APP_NAME}</span>
            <span class="tagline">— {subtitle or APP_TAGLINE}</span>
          </div>
          <div class="timestamp">{now}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f"<div class='section-title'>// {title}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Formatters                                                                  #
# --------------------------------------------------------------------------- #
def fmt_money(value: float, currency: str = "USD", decimals: int = 2) -> str:
    if value is None:
        return "—"
    symbol = {"USD": "$", "COP": "$", "EUR": "€"}.get(currency, "")
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    if currency == "COP":
        # Colombian peso: thousands separator with dot
        formatted = f"{abs_v:,.0f}".replace(",", ".")
    else:
        formatted = f"{abs_v:,.{decimals}f}"
    return f"{sign}{symbol}{formatted}"


def fmt_pct(value: float, decimals: int = 2, sign: bool = True) -> str:
    if value is None:
        return "—"
    s = "+" if (sign and value > 0) else ""
    return f"{s}{value:.{decimals}f}%"


def color_class(value: float) -> str:
    if value is None or value == 0:
        return ""
    return "pos" if value > 0 else "neg"


# --------------------------------------------------------------------------- #
# Metric card                                                                 #
# --------------------------------------------------------------------------- #
def metric_card(label: str, value: str, delta: str | None = None,
                delta_class: str = "", help_text: str | None = None) -> None:
    delta_html = (
        f"<div class='metric-delta {delta_class}'>{delta}</div>" if delta else ""
    )
    help_html = (
        f"<div class='metric-label' style='margin-top:0.5rem;font-size:0.65rem;'>"
        f"{help_text}</div>" if help_text else ""
    )
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          {delta_html}
          {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "neutral") -> str:
    """Return HTML for an inline badge. Use inside other markdown blocks."""
    return f"<span class='badge badge-{kind}'>{text}</span>"
