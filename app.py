import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="On The Moon Portfolio & Sniper Watchlist", page_icon="🌕", layout="wide")

# --- CSS ปรับแต่ง ---
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }
    h3 { padding-top: 1rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 2.2rem !important; }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. Initialize Session State ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
        {"Ticker": "TSM",  "Category": "Growth",    "Avg Cost": 274.9960, "Qty": 0.1118198},
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "AMZN", "Category": "Growth",    "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "NVDA", "Category": "Growth",    "Avg Cost": 178.7260, "Qty": 0.3351499},
    ]

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "WM"]

if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = "* **วิเคราะห์สัปดาห์นี้:** ติดตามตัวเลข CPI และงบ Micron (MU)"

# --- 3. Sidebar ---
with st.sidebar:
    st.header("💼 Wallet Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=400.00, step=10.0)

# --- 4. Data Fetching ---
try:
    now = datetime.utcnow() + timedelta(hours=7)
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")
    
    port_tickers = [item['Ticker'] for item in st.session_state.portfolio]
    all_tickers = list(set(port_tickers + st.session_state.watchlist))

    @st.cache_data(ttl=60)
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True)
        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                data_dict[ticker] = {
                    "Price": df_t['Close'].iloc[-1],
                    "PrevClose": df_t['Close'].iloc[-2],
                    "EMA50": df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1],
                    "Sell1": (df_t['Close'].rolling(window=20).mean() + (df_t['Close'].rolling(window=20).std() * 2)).iloc[-1]
                }
            except: data_dict[ticker] = {"Price": 0, "EMA50": 0}
        return data_dict

    market_data = get_realtime_data(all_tickers)

    # --- 5. UI Display ---
    st.title("🌕 On The Moon Portfolio & Sniper Watchlist")
    
    df = pd.DataFrame(st.session_state.portfolio)
    df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    df['Value USD'] = df['Qty'] * df['Current Price']
    
    total_val = df['Value USD'].sum() + cash_balance_usd
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Value", f"${total_val:,.2f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}")
    c3.metric("📅 Last Update", target_date_str)

    st.markdown("---")
    
    # Portfolio Table
    st.subheader("🚀 On The Moon Holdings")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Watchlist Table
    st.subheader("🎯 Sniper Watchlist")
    watchlist_results = []
    for t in st.session_state.watchlist:
        d = market_data.get(t, {})
        price = d.get('Price', 0)
        ema50 = d.get('EMA50', 0)
        diff = (price - ema50) / ema50 if ema50 > 0 else 0
        
        # แก้ไขจุดที่เคย Error:
        if diff < 0 and price > 0: signal = "✅ IN ZONE"
        elif 0 <= diff <= 0.02: signal = "🟢 ALERT"
        else: signal = "➖ Wait"
        
        watchlist_results.append({"Ticker": t, "Price": price, "Diff EMA50": f"{diff:+.2%}", "Signal": signal})
    
    st.dataframe(pd.DataFrame(watchlist_results), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"แอปขัดข้องชั่วคราว: {e}")
