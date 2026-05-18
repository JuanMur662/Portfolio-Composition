# ◐ Mesa de Trading

Personal portfolio tracker built in Streamlit. Two-broker setup:

- **🇨🇴 Trii** — Colombian BVC + LatAm positions, native COP
- **🌎 eToro** — international positions, native USD

No currency consolidation. Each pestaña runs in its native currency, exactly
as you trade.

---

## ⚡ Quick start (local)

```bash
# 1. Clone or unzip the project
cd portfolio-tracker

# 2. (Recommended) create a virtual env
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

The first time it runs, it creates `data/portfolio.db` (SQLite). That single
file is **your portfolio** — back it up periodically (or let the app export to
Excel from **Ajustes**).

---

## 🗂️ Project structure

```
portfolio-tracker/
├── app.py                  # Main Streamlit entry point
├── core/
│   ├── config.py           # Ticker aliases, sectors, brokers, palette
│   ├── db.py               # SQLite persistence
│   ├── prices.py           # yfinance + manual price overrides
│   ├── metrics.py          # Positions, P&L, XIRR, exposure
│   └── ui.py               # CSS injection + components
├── data/                   # SQLite database lives here (gitignored)
├── .streamlit/config.toml  # Theme
├── requirements.txt
└── README.md
```

---

## 📋 How to use

1. **➕ Nueva transacción** — register a buy or sell.
   Required fields: broker, ticker, action, quantity, price (per share),
   commission, order type, date.

2. **🇨🇴 Trii** / **🌎 eToro** — live positions table with current prices.
   Each row shows cost basis, market value, P&L (absolute + %), and price
   source (🟢 live yfinance, 🟡 manual override, 🔴 unavailable).
   Click any position to expand a detailed view with an embedded TradingView
   mini-chart.

3. **📊 Dashboard** — both brokers side-by-side without consolidation, plus
   exposure breakdowns (country / sector / broker), XIRR per broker, and
   best/worst position highlights.

4. **💵 Dividendos** — register dividends as they're paid. They flow into the
   total P&L automatically.

5. **📜 Histórico** — every closed trade pair (FIFO matched), realized P&L,
   win rate, average holding period.

6. **⚙️ Ajustes** — manual price override for tickers `yfinance` doesn't
   cover (typical for some BVC names). Also: Excel export and delete transactions.

---

## 🎯 Ticker conventions

The app uses Yahoo Finance for live prices. Some Colombian tickers are
covered by their NYSE ADR. Edit `core/config.py → YFINANCE_ALIASES` to add
your own:

| You enter   | Yahoo lookup | Notes                                  |
| ----------- | ------------ | -------------------------------------- |
| `NU`        | `NU`         | Nubank — NYSE                          |
| `ECOPETROL` | `EC`         | Ecopetrol ADR                          |
| `BCOLOMBIA` | `CIB`        | Bancolombia ADR                        |
| `GEB`       | `GEB.CL`     | Try Chilean exchange (may fail — manual fallback) |
| `IYF`       | `IYF`        | iShares U.S. Financials                |
| `XLF`       | `XLF`        | Financial Select SPDR                  |

For anything `yfinance` doesn't cover, go to **Ajustes → Precios manuales**
and key in the current price periodically (e.g., from your broker app).

---

## 🚀 Deploy to Streamlit Community Cloud (free)

1. Push this folder to a new **private GitHub repo** (your portfolio data is in
   `data/portfolio.db`, but that path is `.gitignore`'d — you'll need a
   persistent storage strategy before deploy, see next section).

2. Sign up at [streamlit.io/cloud](https://streamlit.io/cloud) (free, sign in
   with GitHub).

3. **New app** → point at your repo + branch + `app.py`. Deploys in ~2 minutes.

4. You'll get a URL like `https://yourname-portfolio.streamlit.app/` accessible
   from any device.

### Persistence on Streamlit Cloud

The Streamlit Cloud filesystem is **ephemeral** — the SQLite file gets wiped
on every redeploy. Three options:

**Option A — Stay local (recommended to start)**
Run on your laptop. Simplest. Data is yours, no cloud dependency.

**Option B — Supabase (free Postgres)**
Replace the SQLite layer in `core/db.py` with Supabase calls. ~50 lines of
code. Free tier covers this use case 100×. Ask me when you want this.

**Option C — Google Sheets backend**
Use `streamlit-gsheets` to keep the DB in a Google Sheet you own. Excellent
audit trail (you can inspect the data manually). Also ~50 lines to swap.

---

## 🧮 Methodology notes

- **Cost basis**: weighted-average (commissions roll into cost on buys,
  netted from proceeds on sells).
- **Closed positions**: FIFO matching (oldest buy lot pairs with sell first).
- **XIRR**: Newton-Raphson over all cashflows (buys negative, sells/dividends
  positive, plus terminal market value). Annualized.
- **Benchmark**: Trii vs `ICOL` (iShares MSCI Colombia ETF, NYSE — proxy for
  COLCAP). eToro vs `SPY` (S&P 500).

---

## 🔒 Privacy

Your transaction database is **only on your machine** (`data/portfolio.db`).
Nothing is sent anywhere except the public yfinance API requests for
current prices (ticker symbol only, no portfolio data).

---

## 🛠️ Next features (when you want them)

- Cloud persistence (Supabase or Google Sheets)
- Alerts on % moves
- Backtest of your strategy vs benchmark
- TWR computation (currently XIRR only)
- Drawdown chart
- CSV import (bulk historical from broker statements)

Just ask.
