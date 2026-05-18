"""
Mesa de Trading — Portfolio Terminal
Main Streamlit application.

Run locally:
    streamlit run app.py

Deploy:
    Push to GitHub, then deploy via https://streamlit.io/cloud
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import db, metrics, prices, ui
from core.config import (
    APP_NAME, BROKERS, COLORS, TICKER_METADATA, TICKER_NAMES,
)

# --------------------------------------------------------------------------- #
# Page config + bootstrap                                                     #
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title=f"{APP_NAME} · Portfolio Terminal",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()
ui.inject_css()


# --------------------------------------------------------------------------- #
# Sidebar navigation                                                          #
# --------------------------------------------------------------------------- #
def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div style='padding:1rem 0 1.5rem 0; border-bottom:1px solid {COLORS["border"]};
                        margin-bottom:1rem;'>
              <div style='font-family:"JetBrains Mono",monospace; color:{COLORS["accent"]};
                          font-size:0.95rem; font-weight:700; letter-spacing:0.2em;'>
                ◐ MESA
              </div>
              <div style='color:{COLORS["text_muted"]}; font-size:0.72rem;
                          font-family:"JetBrains Mono",monospace; margin-top:0.25rem;'>
                v0.1 · personal terminal
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navegación",
            options=[
                "📊  Dashboard",
                "🇨🇴  Trii",
                "🌎  eToro",
                "➕  Nueva transacción",
                "💵  Dividendos",
                "📜  Histórico",
                "⚙️  Ajustes",
            ],
            label_visibility="collapsed",
            index=0,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↻ Refrescar precios", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.caption(
            f"<span class='mono subtle'>cache · "
            f"{datetime.now().strftime('%H:%M:%S')}</span>",
            unsafe_allow_html=True,
        )

    return page


# --------------------------------------------------------------------------- #
# Pages                                                                       #
# --------------------------------------------------------------------------- #
def page_dashboard() -> None:
    ui.render_header("Portfolio overview · todas las cuentas")

    # Aggregate stats per broker (no consolidation, each in native currency)
    cols = st.columns(2)
    for col, broker_key in zip(cols, ["trii", "etoro"]):
        broker = BROKERS[broker_key]
        stats = metrics.portfolio_stats(broker_key)
        with col:
            st.markdown(
                f"""
                <div style='display:flex; align-items:baseline; gap:0.5rem;
                            margin-bottom:1rem;'>
                  <span style='font-size:1.5rem;'>{broker["flag"]}</span>
                  <span style='font-size:1.15rem; font-weight:700;'>{broker["name"]}</span>
                  <span class='mono subtle' style='font-size:0.75rem;'>
                    · {broker["currency"]} · {broker["region"]}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            inner = st.columns(2)
            with inner[0]:
                ui.metric_card(
                    "Valor de mercado",
                    ui.fmt_money(stats.market_value, broker["currency"]),
                    f"{stats.n_positions} posición(es)",
                    delta_class="muted",
                )
            with inner[1]:
                ui.metric_card(
                    "P&L no realizado",
                    ui.fmt_money(stats.unrealized_pl, broker["currency"]),
                    ui.fmt_pct(stats.unrealized_pl_pct),
                    delta_class=ui.color_class(stats.unrealized_pl),
                )
            inner2 = st.columns(2)
            with inner2[0]:
                ui.metric_card(
                    "P&L realizado",
                    ui.fmt_money(stats.realized_pl, broker["currency"]),
                    "histórico",
                    delta_class=ui.color_class(stats.realized_pl) or "muted",
                )
            with inner2[1]:
                irr = metrics.portfolio_irr(broker_key)
                ui.metric_card(
                    "Retorno anualizado (XIRR)",
                    ui.fmt_pct(irr * 100) if irr is not None else "—",
                    "incl. timing de cashflows",
                    delta_class=ui.color_class((irr or 0) * 100) or "muted",
                )

    # Exposure breakdowns
    ui.section("Exposición")
    e1, e2, e3 = st.columns(3)
    # By country
    by_country = metrics.exposure_by("country")
    by_sector  = metrics.exposure_by("sector")
    by_broker  = metrics.exposure_by("broker")

    with e1:
        st.markdown("<h3>Por país</h3>", unsafe_allow_html=True)
        if not by_country.empty:
            st.plotly_chart(_donut(by_country, "country"), use_container_width=True)
        else:
            st.caption("Sin posiciones")
    with e2:
        st.markdown("<h3>Por sector</h3>", unsafe_allow_html=True)
        if not by_sector.empty:
            st.plotly_chart(_donut(by_sector, "sector"), use_container_width=True)
        else:
            st.caption("Sin posiciones")
    with e3:
        st.markdown("<h3>Por broker</h3>", unsafe_allow_html=True)
        if not by_broker.empty:
            st.plotly_chart(_donut(by_broker, "broker"), use_container_width=True)
        else:
            st.caption("Sin posiciones")

    # Best/worst
    ui.section("Highlights")
    h1, h2 = st.columns(2)
    for col, broker_key in zip([h1, h2], ["trii", "etoro"]):
        stats = metrics.portfolio_stats(broker_key)
        b = BROKERS[broker_key]
        with col:
            st.markdown(
                f"<div class='muted mono' style='font-size:0.8rem;'>"
                f"{b['flag']} {b['name']}</div>",
                unsafe_allow_html=True,
            )
            if stats.best and stats.worst:
                st.markdown(
                    f"""
                    <div class='metric-card'>
                      <div style='display:flex; justify-content:space-between; margin-bottom:0.5rem;'>
                        <span class='muted'>Mejor posición</span>
                        <span class='mono pos'>{stats.best[0]} · {ui.fmt_pct(stats.best[1])}</span>
                      </div>
                      <div style='display:flex; justify-content:space-between;'>
                        <span class='muted'>Peor posición</span>
                        <span class='mono neg'>{stats.worst[0]} · {ui.fmt_pct(stats.worst[1])}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Sin posiciones abiertas")


def page_broker(broker_key: str) -> None:
    broker = BROKERS[broker_key]
    ui.render_header(f"{broker['flag']} {broker['name']} · {broker['region']}")

    stats = metrics.portfolio_stats(broker_key)
    cur = broker["currency"]

    # Top KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Valor de mercado", ui.fmt_money(stats.market_value, cur),
                       f"{stats.n_positions} posición(es)", "muted")
    with c2:
        ui.metric_card("Costo base", ui.fmt_money(stats.cost_basis, cur),
                       "capital invertido (abierto)", "muted")
    with c3:
        ui.metric_card("P&L no realizado",
                       ui.fmt_money(stats.unrealized_pl, cur),
                       ui.fmt_pct(stats.unrealized_pl_pct),
                       ui.color_class(stats.unrealized_pl))
    with c4:
        ui.metric_card("Dividendos",
                       ui.fmt_money(stats.dividends, cur),
                       "recibidos", "muted")

    # Position table
    ui.section("Posiciones abiertas")
    df = metrics.positions_dataframe(broker_key, only_open=True)

    if df.empty:
        st.info("Sin posiciones abiertas en este broker.")
    else:
        # Build display dataframe
        show = pd.DataFrame({
            "Ticker":   df["ticker"],
            "Nombre":   df["name"],
            "Sector":   df["sector"],
            "País":     df["country"],
            "Cant.":    df["quantity"].map(lambda x: f"{x:,.4f}".rstrip("0").rstrip(".")),
            "Costo avg": df.apply(
                lambda r: ui.fmt_money(r["avg_cost"], r["currency"]), axis=1),
            "Precio":    df.apply(
                lambda r: ui.fmt_money(r["current_price"], r["currency"]), axis=1),
            "Valor mkt": df.apply(
                lambda r: ui.fmt_money(r["market_value"], r["currency"]), axis=1),
            "P&L":       df.apply(
                lambda r: ui.fmt_money(r["unrealized_pl"], r["currency"]), axis=1),
            "P&L %":     df["unrealized_pl_pct"].map(lambda x: ui.fmt_pct(x)),
            "Fuente":    df["price_source"].map(
                {"yfinance": "🟢 live", "manual": "🟡 manual",
                 "unavailable": "🔴 N/A"}),
        })

        # Style P&L column with HTML
        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker":  st.column_config.TextColumn(width="small"),
                "P&L":     st.column_config.TextColumn(width="medium"),
                "P&L %":   st.column_config.TextColumn(width="small"),
            },
        )

        # Warn about unavailable prices
        missing = df[df["price_source"] == "unavailable"]
        if not missing.empty:
            st.warning(
                f"⚠ Sin precio en vivo para: **{', '.join(missing['ticker'])}**. "
                "Ve a **Ajustes → Precios manuales** para ingresarlos."
            )

        # Per-position detail expanders with TradingView chart
        ui.section("Detalle por posición")
        for _, row in df.iterrows():
            with st.expander(
                f"  {row['ticker']} · {row['name']}  ·  "
                f"{ui.fmt_pct(row['unrealized_pl_pct'])}",
                expanded=False,
            ):
                d1, d2 = st.columns([1, 2])
                with d1:
                    st.markdown(
                        f"""
                        - **Cantidad**: `{row['quantity']:,.4f}`
                        - **Costo promedio**: `{ui.fmt_money(row['avg_cost'], row['currency'])}`
                        - **Comisiones**: `{ui.fmt_money(row['commissions_total'], row['currency'])}`
                        - **Última operación**: `{row['last_action_date']}`
                        - **P&L realizado (histórico)**: `{ui.fmt_money(row['realized_pl'], row['currency'])}`
                        """
                    )
                with d2:
                    _tradingview_chart(row["ticker"], height=320)


def _tradingview_chart(ticker: str, height: int = 380) -> None:
    """Embed TradingView mini-chart widget for a ticker."""
    # Build a reasonable TV symbol — fallback to plain ticker
    tv_symbol = ticker
    if ticker in {"NU", "IYF", "XLF", "SPY", "QQQ", "ICOL", "IYG", "VFH"}:
        tv_symbol = f"NYSE:{ticker}" if ticker not in {"QQQ", "SPY"} else f"AMEX:{ticker}"
    html = f"""
    <div class="tradingview-widget-container" style='border:1px solid {COLORS["border"]};
         border-radius:8px; overflow:hidden;'>
      <div id="tv_{ticker}"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js"
        async>
        {{
          "symbol": "{tv_symbol}",
          "width": "100%",
          "height": "{height}",
          "locale": "es",
          "dateRange": "3M",
          "colorTheme": "dark",
          "isTransparent": true,
          "autosize": true,
          "largeChartUrl": ""
        }}
      </script>
    </div>
    """
    st.components.v1.html(html, height=height + 20)


def _donut(df: pd.DataFrame, label_col: str) -> go.Figure:
    fig = go.Figure(
        data=[go.Pie(
            labels=df[label_col],
            values=df["market_value"],
            hole=0.65,
            textinfo="label+percent",
            textfont=dict(family="JetBrains Mono", size=11, color=COLORS["text"]),
            marker=dict(
                colors=[COLORS["accent"], COLORS["secondary"], COLORS["positive"],
                        "#8b5cf6", "#ec4899", "#f59e0b", "#84cc16"],
                line=dict(color=COLORS["bg"], width=2),
            ),
        )]
    )
    fig.update_layout(
        height=260,
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]),
    )
    return fig


# --------------------------------------------------------------------------- #
# Add transaction                                                              #
# --------------------------------------------------------------------------- #
def page_add_transaction() -> None:
    ui.render_header("Registrar nueva transacción")

    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        with st.form("tx_form", clear_on_submit=True):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                broker = st.selectbox(
                    "Broker",
                    options=list(BROKERS.keys()),
                    format_func=lambda k: f"{BROKERS[k]['flag']} {BROKERS[k]['name']} "
                                          f"({BROKERS[k]['currency']})",
                )
            with r1c2:
                action = st.selectbox("Acción", ["buy", "sell"],
                                      format_func=lambda x: "Compra" if x == "buy" else "Venta")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                ticker = st.text_input("Ticker (ej: NU, GEB, IYF)", "").upper().strip()
            with r2c2:
                quantity = st.number_input("Cantidad", min_value=0.0,
                                           step=1.0, format="%.4f")

            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                price = st.number_input(
                    f"Precio por acción ({BROKERS[broker]['currency']})",
                    min_value=0.0, step=0.01, format="%.4f",
                )
            with r3c2:
                commission = st.number_input(
                    "Comisión total", min_value=0.0, step=100.0, format="%.2f",
                    help="Comisión + IVA + impuestos cargados a esta operación",
                )
            with r3c3:
                order_type = st.selectbox("Tipo de orden", ["market", "limit"])

            r4c1, r4c2 = st.columns(2)
            with r4c1:
                trade_date = st.date_input("Fecha de operación", value=date.today())
            with r4c2:
                currency = st.text_input("Moneda", BROKERS[broker]["currency"])

            notes = st.text_area("Notas / tesis (opcional)", height=80)

            submit = st.form_submit_button("💾  Registrar transacción",
                                           type="primary", use_container_width=True)

            if submit:
                if not ticker or quantity <= 0 or price <= 0:
                    st.error("Ticker, cantidad y precio son obligatorios.")
                else:
                    tx = db.Transaction(
                        broker=broker, ticker=ticker, action=action,
                        quantity=quantity, price=price, currency=currency,
                        commission=commission, order_type=order_type,
                        trade_date=trade_date, notes=notes or None,
                    )
                    tx_id = db.add_transaction(tx)
                    st.cache_data.clear()
                    st.success(f"✓ Transacción #{tx_id} registrada.")

    with col_right:
        st.markdown("<h3>Vista previa</h3>", unsafe_allow_html=True)
        st.caption(
            f"<span class='mono subtle'>// últimas 5 transacciones en este broker</span>",
            unsafe_allow_html=True,
        )
        recent = db.get_transactions()
        if not recent.empty:
            recent = recent.sort_values("created_at", ascending=False).head(5)
            for _, r in recent.iterrows():
                action_color = "pos" if r["action"] == "buy" else "neg"
                action_text = "COMPRA" if r["action"] == "buy" else "VENTA"
                st.markdown(
                    f"""
                    <div class='metric-card' style='margin-bottom:0.5rem; padding:0.75rem 1rem;'>
                      <div style='display:flex; justify-content:space-between;'>
                        <span class='mono'><b>{r["ticker"]}</b> · {r["broker"]}</span>
                        <span class='mono {action_color}' style='font-size:0.75rem;'>{action_text}</span>
                      </div>
                      <div class='subtle mono' style='font-size:0.75rem; margin-top:0.25rem;'>
                        {r["quantity"]:,.4f} @ {ui.fmt_money(r["price"], r["currency"])}
                        · {r["trade_date"].date() if hasattr(r["trade_date"], "date") else r["trade_date"]}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Sin transacciones aún.")


# --------------------------------------------------------------------------- #
# Dividends                                                                   #
# --------------------------------------------------------------------------- #
def page_dividends() -> None:
    ui.render_header("Dividendos recibidos")
    col_form, col_list = st.columns([1, 1.5])

    with col_form:
        st.markdown("<h3>Registrar dividendo</h3>", unsafe_allow_html=True)
        with st.form("div_form", clear_on_submit=True):
            broker = st.selectbox(
                "Broker", list(BROKERS.keys()),
                format_func=lambda k: f"{BROKERS[k]['flag']} {BROKERS[k]['name']}",
            )
            ticker = st.text_input("Ticker").upper().strip()
            amount = st.number_input("Monto neto recibido",
                                     min_value=0.0, step=0.01, format="%.2f")
            currency = st.text_input("Moneda", BROKERS[broker]["currency"])
            pay_date = st.date_input("Fecha de pago", value=date.today())
            notes = st.text_area("Notas", height=60)
            submit = st.form_submit_button("💾  Registrar",
                                           type="primary", use_container_width=True)
            if submit:
                if not ticker or amount <= 0:
                    st.error("Ticker y monto son obligatorios.")
                else:
                    db.add_dividend(db.Dividend(
                        broker=broker, ticker=ticker, amount=amount,
                        currency=currency, pay_date=pay_date, notes=notes or None,
                    ))
                    st.cache_data.clear()
                    st.success("✓ Dividendo registrado.")

    with col_list:
        st.markdown("<h3>Histórico</h3>", unsafe_allow_html=True)
        divs = db.get_dividends()
        if divs.empty:
            st.caption("Sin dividendos registrados.")
        else:
            show = divs.copy()
            show["Monto"] = show.apply(
                lambda r: ui.fmt_money(r["amount"], r["currency"]), axis=1)
            show["Fecha"] = show["pay_date"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                show[["Fecha", "broker", "ticker", "Monto", "notes"]]
                  .rename(columns={"broker": "Broker", "ticker": "Ticker",
                                   "notes": "Notas"}),
                use_container_width=True, hide_index=True,
            )


# --------------------------------------------------------------------------- #
# History (closed positions)                                                  #
# --------------------------------------------------------------------------- #
def page_history() -> None:
    ui.render_header("Histórico de posiciones cerradas")

    tabs = st.tabs(["🇨🇴 Trii", "🌎 eToro", "Todas"])
    for tab, broker_key in zip(tabs, ["trii", "etoro", None]):
        with tab:
            df = metrics.closed_positions(broker_key)
            if df.empty:
                st.caption("No hay posiciones cerradas todavía.")
                continue

            # KPIs
            total_realized = df["realized_pl"].sum()
            wins = (df["realized_pl"] > 0).sum()
            losses = (df["realized_pl"] < 0).sum()
            win_rate = wins / max(wins + losses, 1) * 100
            avg_hold = df["holding_days"].mean()

            kp1, kp2, kp3, kp4 = st.columns(4)
            with kp1:
                ui.metric_card("Trades cerrados", str(len(df)), "", "muted")
            with kp2:
                ccy = df["currency"].iloc[0] if len(df) else "USD"
                ui.metric_card(
                    "P&L realizado total",
                    ui.fmt_money(total_realized, ccy),
                    "", ui.color_class(total_realized),
                )
            with kp3:
                ui.metric_card("Win rate", ui.fmt_pct(win_rate, sign=False),
                               f"{wins}W · {losses}L", "muted")
            with kp4:
                ui.metric_card("Holding promedio",
                               f"{avg_hold:.0f} días", "", "muted")

            # Table
            show = df.copy()
            show["Compra"] = pd.to_datetime(show["buy_date"]).dt.strftime("%Y-%m-%d")
            show["Venta"]  = pd.to_datetime(show["sell_date"]).dt.strftime("%Y-%m-%d")
            show["Precio compra"] = show.apply(
                lambda r: ui.fmt_money(r["buy_price"], r["currency"]), axis=1)
            show["Precio venta"]  = show.apply(
                lambda r: ui.fmt_money(r["sell_price"], r["currency"]), axis=1)
            show["P&L"] = show.apply(
                lambda r: ui.fmt_money(r["realized_pl"], r["currency"]), axis=1)
            show["Retorno %"] = show["return_pct"].map(lambda x: ui.fmt_pct(x))

            display_cols = [
                "broker", "ticker", "name", "quantity",
                "Compra", "Precio compra", "Venta", "Precio venta",
                "P&L", "Retorno %", "holding_days",
            ]
            st.dataframe(
                show[display_cols].rename(columns={
                    "broker": "Broker", "ticker": "Ticker", "name": "Nombre",
                    "quantity": "Cant.", "holding_days": "Días",
                }),
                use_container_width=True, hide_index=True,
            )


# --------------------------------------------------------------------------- #
# Settings                                                                    #
# --------------------------------------------------------------------------- #
def page_settings() -> None:
    ui.render_header("Ajustes")

    ui.section("Precios manuales (override)")
    st.caption(
        "Usa esto para tickers que `yfinance` no cubra (típico en BVC). "
        "El precio manual tiene precedencia sobre el live."
    )

    txs = db.get_transactions()
    if not txs.empty:
        active_tickers = sorted(txs["ticker"].unique())
        for ticker in active_tickers:
            ccy = txs[txs["ticker"] == ticker]["currency"].iloc[-1]
            quote = prices.get_price(ticker, ccy)
            existing = db.get_manual_price(ticker)

            cols = st.columns([2, 2, 2, 1])
            with cols[0]:
                st.markdown(
                    f"<div style='padding-top:0.5rem;'><b class='mono'>{ticker}</b> "
                    f"<span class='subtle mono' style='font-size:0.75rem;'>· {ccy}</span></div>",
                    unsafe_allow_html=True,
                )
            with cols[1]:
                status = (
                    f"🟢 yfinance · {ui.fmt_money(quote.price, ccy)}"
                    if quote.source == "yfinance" else
                    f"🟡 manual · {ui.fmt_money(quote.price, ccy)}"
                    if quote.source == "manual" else
                    "🔴 sin fuente"
                )
                st.markdown(
                    f"<div style='padding-top:0.5rem;' class='mono subtle'>{status}</div>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                new_price = st.number_input(
                    f"Precio manual ({ccy})",
                    value=float(existing[0]) if existing else 0.0,
                    min_value=0.0, step=0.01, format="%.4f",
                    key=f"mp_{ticker}", label_visibility="collapsed",
                )
            with cols[3]:
                if st.button("Guardar", key=f"mp_save_{ticker}"):
                    if new_price > 0:
                        db.set_manual_price(ticker, new_price, ccy)
                        st.cache_data.clear()
                        st.success(f"{ticker} → {ui.fmt_money(new_price, ccy)}")
                        st.rerun()
    else:
        st.caption("No hay transacciones registradas aún.")

    # Export
    ui.section("Backup")
    if st.button("📥  Exportar todo a Excel"):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet, df in db.export_all().items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sheet, index=False)
        st.download_button(
            "⬇ Descargar portfolio.xlsx",
            data=buffer.getvalue(),
            file_name=f"portfolio_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Transaction management
    ui.section("Editar / eliminar transacciones")
    txs = db.get_transactions()
    if txs.empty:
        st.caption("Sin transacciones.")
    else:
        show = txs.copy()
        show["trade_date"] = show["trade_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(show, use_container_width=True, hide_index=True)
        tx_id = st.number_input("ID de transacción a eliminar",
                                min_value=0, step=1, value=0)
        if tx_id and st.button("🗑  Eliminar transacción", type="primary"):
            db.delete_transaction(int(tx_id))
            st.cache_data.clear()
            st.success(f"Transacción #{tx_id} eliminada.")
            st.rerun()


# --------------------------------------------------------------------------- #
# Router                                                                      #
# --------------------------------------------------------------------------- #
PAGES = {
    "📊  Dashboard":         page_dashboard,
    "🇨🇴  Trii":              lambda: page_broker("trii"),
    "🌎  eToro":             lambda: page_broker("etoro"),
    "➕  Nueva transacción": page_add_transaction,
    "💵  Dividendos":         page_dividends,
    "📜  Histórico":          page_history,
    "⚙️  Ajustes":            page_settings,
}


def main() -> None:
    page = sidebar()
    PAGES[page]()


if __name__ == "__main__":
    main()
