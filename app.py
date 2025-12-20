import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Sniper Portfolio & Watchlist", page_icon="🔭", layout="wide")

# --- CSS ปรับแต่ง (Big Font Edition 🔍) ---
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
    st.session_state.watchlist = [
        "AMZN", "NVDA", "V", "VOO", "GOOGL", "META", "MSFT", "TSLA", 
        "WBD", "AMD", "AVGO", "IREN", "RKLB", "UBER", "CDNS", "WM", "AAPL", "PLTR"
    ]

if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **Update 19 Dec:** เงินเฟ้อลดเหลือ 2.7% (To the Moon 🚀)
* **กลยุทธ์:** ใช้บาทแข็ง (31.34) แลก USD เตรียม Sniper หุ้น Zone A/B ที่ย่อตัว"""

# --- 3. Sidebar Management ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=0.00, step=10.0, format="%.2f")
    st.divider()
    if st.button('🔄 Refresh Data (Real-time)'):
        st.cache_data.clear()
        st.rerun()

# --- 4. PRB Tier Mapping ---
prb_tiers = {
    "NVDA": "S+", "AAPL": "S+", "MSFT": "S+", "GOOGL": "S+", "TSM": "S+", 
    "AMD": "S", "PLTR": "S", "AMZN": "S", "META": "S", "AVGO": "S", 
    "TSLA": "A+", "V": "A+", "LLY": "A+", "VOO": "ETF"
}

# --- 5. Data Fetching (Fixed threads=False) ---
try:
    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))
    
    @st.cache_data(ttl=120)
    def get_realtime_data(tickers_list):
        data_dict = {}
        try:
            # แก้ไข: ใช้ threads=False เพื่อความเสถียรของระบบคลาวด์
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=False, progress=False)
            for ticker in tickers_list:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                if df_t.empty: continue
                
                # Indicators
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                rsi = 50 # Default
                if len(df_t) > 14:
                    delta = df_t['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi = 100 - (100 / (1 + (gain/loss).iloc[-1]))

                data_dict[ticker] = {
                    "Price": df_t['Close'].iloc[-1], "PrevClose": df_t['Close'].iloc[-2],
                    "EMA50": ema50, "RSI": rsi,
                    "Sell1": (df_t['Close'].rolling(window=20).mean() + (df_t['Close'].rolling(window=20).std() * 2)).iloc[-1]
                }
        except: pass
        return data_dict

    market_data = get_realtime_data(all_tickers)

    # --- 6. UI Display ---
    st.title("🔭 Sniper Portfolio & Watchlist")
    
    # คำนวณ Portfolio Metrics
    df = pd.DataFrame(st.session_state.portfolio)
    df['Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    df['Value'] = df['Qty'] * df['Price']
    df['Cost'] = df['Qty'] * df['Avg Cost']
    total_value = df['Value'].sum() + cash_balance_usd
    total_gain = df['Value'].sum() - df['Cost'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*31.34:,.0f}")
    c2.metric("📈 Total Gain", f"${total_gain:+.2f}", f"{(total_gain/df['Cost'].sum()*100):.2f}%")
    c3.metric("🌊 Cash", f"${cash_balance_usd:,.2f}", "Ready to Sniper")

    st.divider()
    
    # Portfolio Table
    col_port, col_watch = st.columns([1.2, 1])
    
    with col_port:
        st.subheader("🚀 My Assets")
        st.dataframe(df[['Ticker', 'Qty', 'Avg Cost', 'Price', 'Value']].style.format({
            "Avg Cost": "${:.2f}", "Price": "${:.2f}", "Value": "${:.2f}"
        }), use_container_width=True, hide_index=True)

    with col_watch:
        st.subheader("🎯 Sniper Watchlist")
        watch_rows = []
        for t in st.session_state.watchlist:
            d = market_data.get(t, {})
            price = d.get('Price', 0)
            ema50 = d.get('EMA50', 0)
            if price > 0:
                diff = (price - ema50) / ema50
                status = "✅ IN ZONE" if diff < 0 else "➖ Wait"
                watch_rows.append({"Symbol": t, "Price": price, "Diff S1": diff, "Status": status})
        
        st.dataframe(pd.DataFrame(watch_rows).sort_values("Diff").style.format({
            "Price": "${:.2f}", "Diff S1": "{:+.1%}"
        }), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Execution Error: {e}")
