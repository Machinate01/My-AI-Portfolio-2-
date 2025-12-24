import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- CONFIGURATION ---
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
REFRESH_RATE = 60  # ปรับลดเหลือ 1 นาทีเพื่อให้ข้อมูลสดใหม่ขึ้น

# --- 1. SETUP PAGE ---
st.set_page_config(page_title="My Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }
    h3 { padding-top: 1rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 2.2rem !important; }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LAYER (SRP) ---

@st.cache_data(ttl=REFRESH_RATE)
def get_market_data(tickers):
    """ดึงข้อมูลจาก Yahoo Finance พร้อมระบบจัดการ Error (ป้องกันข้อมูลเป็น 0)"""
    if not tickers: return {}
    try:
        data = yf.download(tickers, period="2y", group_by='ticker', auto_adjust=True)
        processed = {}
        for t in tickers:
            try:
                df_t = data[t].dropna() if len(tickers) > 1 else data.dropna()
                if df_t.empty: continue
                
                curr_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                ema50 = df_t['Close'].ewm(span=EMA_FAST, adjust=False).mean().iloc[-1]
                ema200 = df_t['Close'].ewm(span=EMA_SLOW, adjust=False).mean().iloc[-1]
                
                # RSI Calculation
                delta = df_t['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(window=RSI_PERIOD).mean()
                loss = -delta.where(delta < 0, 0).rolling(window=RSI_PERIOD).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1]))

                processed[t] = {
                    "Price": curr_price, "PrevClose": prev_close,
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi,
                    "Sell1": (df_t['Close'].rolling(20).mean() + (df_t['Close'].rolling(20).std() * 2)).iloc[-1]
                }
            except: continue
        return processed
    except: return {}

# --- 3. STYLING LOGIC (DRY) ---

def apply_portfolio_style(res_df):
    """ฟังก์ชันรวมการระบายสีตามเงื่อนไข (Price และ Value เปลี่ยนตาม Gain)"""
    def color_logic(row):
        color = '#28a745' if row['Total Gain ($)'] >= 0 else '#dc3545'
        # Requirement: Price และ Value ($) ใช้สีตาม Total Gain ($)
        styles = [''] * len(row)
        idx_price = res_df.columns.get_loc("Price")
        idx_value = res_df.columns.get_loc("Value ($)")
        styles[idx_price] = f'color: {color}'
        styles[idx_value] = f'color: {color}'
        return styles

    return res_df.style.format({
        "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost ($)": "${:,.2f}",
        "Price": "${:.2f}", "Value ($)": "${:,.2f}", "Total Gain ($)": "${:,.2f}",
        "% Total": "{:+.2%}", "Upside": "{:+.1%}", "Diff S1": "{:+.1%}",
        "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"
    }).map(lambda x: 'color: #28a745' if x >= 0 else 'color: #dc3545', subset=['% Total', 'Total Gain ($)', 'Upside'])\
      .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1'])\
      .apply(color_logic, axis=1)

# --- 4. MAIN APP ---

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "AMZN", "Category": "Growth", "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "NVDA", "Category": "Growth", "Avg Cost": 178.7260, "Qty": 0.3351499},
        {"Ticker": "TSM",  "Category": "Growth", "Avg Cost": 274.9960, "Qty": 0.1118198},
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
    ]

with st.sidebar:
    st.header("💼 Wallet")
    cash_bal = st.number_input("Cash Flow ($)", value=400.0, step=10.0)
    if st.button('🔄 Force Refresh'):
        st.cache_data.clear()
        st.rerun()

all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA"]))
market_info = get_market_data(all_tickers)

# Process DataFrame
df = pd.DataFrame(st.session_state.portfolio)
if not df.empty:
    df['Price'] = df['Ticker'].apply(lambda x: market_info.get(x, {}).get('Price', 0))
    df['Total Cost ($)'] = df['Qty'] * df['Avg Cost']
    df['Value ($)'] = df['Qty'] * df['Price']
    df['Total Gain ($)'] = df['Value ($)'] - df['Total Cost ($)']
    df['% Total'] = (df['Price'] - df['Avg Cost']) / df['Avg Cost']
    df['Buy Lv.1'] = df['Ticker'].apply(lambda x: market_info.get(x, {}).get('EMA50', 0))
    df['Buy Lv.2'] = df['Ticker'].apply(lambda x: market_info.get(x, {}).get('EMA200', 0))
    df['Diff S1'] = (df['Price'] - df['Buy Lv.1']) / df['Buy Lv.1']
    df['Upside'] = (df['Ticker'].apply(lambda x: market_info.get(x, {}).get('Sell1', 0)) - df['Price']) / df['Price']

# UI Display
st.title("🔭 My Portfolio & Sniper Watchlist")
c1, c2, c3 = st.columns(3)
total_val = df['Value ($)'].sum() + cash_bal
c1.metric("💰 Total Portfolio Value", f"${total_val:,.2f}")
c2.metric("🌊 Cash Available", f"${cash_bal:,.2f}")
c3.metric("📈 Unrealized P/L", f"${df['Total Gain ($)'].sum():,.2f}")

st.markdown("---")

# Portfolio Order: Ticker -> Qty -> Avg Cost -> Total Cost -> % Total -> Price -> Value -> Total Gain -> Upside -> Diff S1 -> Buy 1 -> Buy 2
col_order = ["Ticker", "Qty", "Avg Cost", "Total Cost ($)", "% Total", "Price", "Value ($)", "Total Gain ($)", "Upside", "Diff S1", "Buy Lv.1", "Buy Lv.2"]

st.subheader("🚀 Growth Engine")
st.dataframe(apply_portfolio_style(df[df['Category'] == 'Growth']), column_order=col_order, hide_index=True)

st.subheader("🛡️ Defensive Wall")
st.dataframe(apply_portfolio_style(df[df['Category'] == 'Defensive']), column_order=col_order, hide_index=True)
