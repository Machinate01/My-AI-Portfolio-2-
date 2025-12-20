import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="My Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

# --- CSS ปรับแต่ง (คงรูปแบบเดิมตามข้อ 3) ---
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }
    h3 { padding-top: 1rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 2.2rem !important; }
    .streamlit-expanderContent p, .streamlit-expanderContent li, .stMarkdown p { font-size: 1.2rem !important; }
    div[data-testid="stDataFrame"] { width: 100%; }
    .stAlert { margin-top: 1rem; }
    textarea { font-size: 1.1rem !important; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. Initialize Session State ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "AMZN", "Category": "Growth", "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "NVDA", "Category": "Growth", "Avg Cost": 178.7260, "Qty": 0.3351499},
        {"Ticker": "TSM",  "Category": "Growth", "Avg Cost": 274.9960, "Qty": 0.1118198},
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
    ]

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "WBD", "AMD", "AVGO", "IREN", "RKLB", "UBER", "CDNS", "WM"]

if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**\n* **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ\n* **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**\n* **Event:** งบ **Micron (MU)** 🚨\n* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI"**\n* **CPI > 3.1%:** Tech ร่วงก่อน"""

# --- 3. Sidebar ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=400.00, step=10.0, format="%.2f")
    st.divider()
    tab_add, tab_remove = st.tabs(["➕ Add Asset", "🗑️ Remove/Sell"])
    with tab_add:
        st.subheader("Add to Portfolio")
        with st.form("add_port"):
            p_ticker = st.text_input("Ticker").upper()
            p_qty = st.number_input("Qty", min_value=0.0001, format="%.4f")
            p_cost = st.number_input("Avg Cost", min_value=0.0, format="%.2f")
            p_cat = st.selectbox("Category", ["Growth", "Defensive"])
            if st.form_submit_button("Add Position"):
                if p_ticker:
                    st.session_state.portfolio.append({"Ticker": p_ticker, "Category": p_cat, "Avg Cost": p_cost, "Qty": p_qty})
                    st.rerun()

# --- 4. PRB Tier Mapping ---
prb_tiers = {"NVDA": "S+", "AAPL": "S+", "MSFT": "S+", "GOOGL": "S+", "TSM": "S+", "AMZN": "S", "META": "S", "V": "A+", "LLY": "A+", "VOO": "ETF"}

# --- 5. Data Fetching ---
try:
    now = datetime.utcnow() + timedelta(hours=7)
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")
    port_tickers = [item['Ticker'] for item in st.session_state.portfolio]
    all_tickers = list(set(port_tickers + st.session_state.watchlist))

    @st.cache_data(ttl=60)
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=True)
        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                rsi = (100 - (100 / (1 + (df_t['Close'].diff().where(df_t['Close'].diff() > 0, 0).rolling(14).mean() / -df_t['Close'].diff().where(df_t['Close'].diff() < 0, 0).rolling(14).mean())))).iloc[-1]
                data_dict[ticker] = {
                    "Price": df_t['Close'].iloc[-1], "PrevClose": df_t['Close'].iloc[-2],
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi,
                    "Sell1": (df_t['Close'].rolling(20).mean() + (df_t['Close'].rolling(20).std() * 2)).iloc[-1]
                }
            except: data_dict[ticker] = {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0}
        return data_dict

    market_data = get_realtime_data(all_tickers)

    # --- 6. Data Processing ---
    df = pd.DataFrame(st.session_state.portfolio)
    if not df.empty:
        df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
        df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
        df['Value USD'] = df['Qty'] * df['Current Price']
        df['Total Cost'] = df['Qty'] * df['Avg Cost']
        df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
        df['% P/L'] = (df['Current Price'] - df['Avg Cost']) / df['Avg Cost']
        df['Buy Lv.1'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA50', 0))
        df['Buy Lv.2'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA200', 0))
        df['Diff S1'] = (df['Current Price'] - df['Buy Lv.1']) / df['Buy Lv.1']
        df['Upside'] = (df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Sell1', 0)) - df['Current Price']) / df['Current Price']

    # --- 7. Styling Functions ---
    def color_text(val):
        return 'color: #28a745' if val >= 0 else 'color: #dc3545'

    def style_portfolio(res_df):
        # ฟังก์ชันพิเศษสำหรับข้อ 1: ระบายสี Value ตาม Gain
        def apply_value_color(row):
            gain_color = '#28a745' if row['Total Gain USD'] >= 0 else '#dc3545'
            return [f'color: {gain_color}' if col == 'Value USD' else '' for col in row.index]

        return res_df.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
            "Diff S1": "{:+.1%}", "% P/L": "{:+.2%}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
            "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"
        }).map(color_text, subset=['% P/L', 'Total Gain USD', 'Upside']).apply(apply_value_color, axis=1)

    # --- 8. UI Display ---
    st.title("🔭 My Portfolio & Sniper Watchlist")
    
    # Metrics
    total_invested = df['Total Cost'].sum()
    total_val = df['Value USD'].sum() + cash_balance_usd
    total_gain = df['Total Gain USD'].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_val:,.2f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Invested: ${total_invested:,.0f}")
    c4.metric("📅 Last Update", now.strftime("%H:%M:%S"))

    st.markdown("---")

    col_bot_left, col_bot_right = st.columns(2)

    with col_bot_left:
        # Growth Engine
        st.subheader("🚀 Growth Engine")
        df_growth = df[df['Category'] == 'Growth'].copy()
        # เพิ่ม Total Cost (ข้อ 2) และสลับคอลัมน์ (ข้อ 4)
        cols = ["Ticker", "Qty", "Avg Cost", "Total Cost", "Current Price", "% P/L", "Value USD", "Total Gain USD", "Upside", "Diff S1", "Buy Lv.1", "Buy Lv.2"]
        st.dataframe(style_portfolio(df_growth), column_order=cols, hide_index=True, use_container_width=True)

        # Defensive Wall
        st.subheader("🛡️ Defensive Wall")
        df_def = df[df['Category'] == 'Defensive'].copy()
        st.dataframe(style_portfolio(df_def), column_order=cols, hide_index=True, use_container_width=True)

    with col_bot_right:
        st.subheader("🎯 Sniper Watchlist")
        # Watchlist logic คงเดิมตามคำขอข้อ 3
        watchlist_data = []
        for t in sorted(st.session_state.watchlist):
            d = market_data.get(t, {})
            price = d.get('Price', 0)
            buy1 = d.get('EMA50', 0)
            diff_s1 = (price - buy1)/buy1 if buy1 > 0 else 0
            status = "✅ IN ZONE" if diff_s1 < 0 else "🟢 ALERT" if diff_s1 < 0.02 else "➖ Wait"
            watchlist_data.append({"Ticker": t, "Price": price, "Status": status, "Diff S1": diff_s1, "RSI": d.get('RSI', 50)})
        
        st.dataframe(pd.DataFrame(watchlist_data).style.format({"Price": "${:.2f}", "Diff S1": "{:+.1%}"}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
