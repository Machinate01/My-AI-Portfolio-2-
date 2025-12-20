import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="My Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

# --- CSS ปรับแต่ง UI ให้ดูคมชัดแบบ Dark Mode ---
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }
    h3 { padding-top: 1rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 2.2rem !important; }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. Initialize Session State (หุ้น 6 ตัวตามพอร์ตของคุณ) ---
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
    st.session_state.watchlist = ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "WM"]

# --- 3. Sidebar ---
with st.sidebar:
    st.header("💼 Wallet Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=400.00, step=10.0, format="%.2f")

# --- 4. PRB Tier Mapping ---
prb_tiers = {"NVDA": "S+", "TSM": "S+", "AMZN": "S", "V": "A+", "LLY": "A+", "VOO": "ETF"}

# --- 5. Data Fetching ---
try:
    now = datetime.utcnow() + timedelta(hours=7)
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")
    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))

    @st.cache_data(ttl=60)
    def get_realtime_data(tickers_list):
        data_dict = {}
        df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True)
        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                df_t['EMA50'] = df_t['Close'].ewm(span=50, adjust=False).mean()
                df_t['SMA20'] = df_t['Close'].rolling(window=20).mean()
                df_t['STD20'] = df_t['Close'].rolling(window=20).std()
                data_dict[ticker] = {
                    "Price": df_t['Close'].iloc[-1],
                    "PrevClose": df_t['Close'].iloc[-2],
                    "EMA50": df_t['EMA50'].iloc[-1],
                    "Sell1": (df_t['SMA20'] + (df_t['STD20'] * 2)).iloc[-1]
                }
            except: pass
        return data_dict

    market_data = get_realtime_data(all_tickers)

    # --- 6. Data Processing ---
    df = pd.DataFrame(st.session_state.portfolio)
    df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
    
    # คำนวณต้นทุนและมูลค่า
    df['Total Cost'] = df['Qty'] * df['Avg Cost'] 
    df['Value USD'] = df['Qty'] * df['Current Price']
    df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
    df['% P/L'] = (df['Current Price'] - df['Avg Cost']) / df['Avg Cost']

    # คำนวณ Sniper Levels
    def get_levels(row):
        d = market_data.get(row['Ticker'], {})
        buy1 = d.get('EMA50', 0)
        sell1 = d.get('Sell1', 0)
        diff_s1 = (row['Current Price'] - buy1) / buy1 if buy1 > 0 else 0
        upside = (sell1 - row['Current Price']) / row['Current Price'] if row['Current Price'] > 0 else 0
        return pd.Series([buy1, sell1, diff_s1, upside], index=['Buy Lv.1', 'Sell Lv.1', 'Diff S1', 'Upside'])

    df[['Buy Lv.1', 'Sell Lv.1', 'Diff S1', 'Upside']] = df.apply(get_levels, axis=1)

    # ฟังก์ชันสี
    def color_pl(val): return 'color: #28a745' if val >= 0 else 'color: #dc3545'
    def format_pct(val): return f"{val:+.2%}"

    # --- 7. UI Display ---
    st.title("🔭 My Portfolio & Sniper Watchlist")
    
    # Metrics
    total_val = df['Value USD'].sum() + cash_balance_usd
    total_invested = df['Total Cost'].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value", f"${total_val:,.2f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}")
    c3.metric("📈 Unrealized G/L", f"${(total_val - total_invested - cash_balance_usd):,.2f}")
    c4.metric("🕒 Update", now.strftime("%H:%M"))

    st.markdown("---")

    # ลำดับคอลัมน์ที่ต้องการแสดง (เพิ่ม Total Cost หลัง Avg Cost)
    display_cols = ["Ticker", "Qty", "Avg Cost", "Total Cost", "% P/L", "Current Price", "Value USD", "Total Gain USD", "Upside", "Diff S1", "Buy Lv.1", "Sell Lv.1"]

    # --- ตาราง 1: Growth Engine ---
    st.subheader("🚀 Growth Engine")
    df_growth = df[df['Category'] == 'Growth'].copy()
    if not df_growth.empty:
        st.dataframe(
            df_growth.style.format({
                "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", 
                "Current Price": "${:.2f}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                "% P/L": format_pct, "Upside": "{:+.1%}", "Diff S1": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Sell Lv.1": "${:.0f}"
            }).map(color_pl, subset=['% P/L', 'Total Gain USD', 'Upside']),
            column_order=display_cols,
            column_config={
                "Total Cost": "Total Cost (USD)", 
                "% P/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)"
            },
            hide_index=True, use_container_width=True
        )

    # --- ตาราง 2: Defensive Wall ---
    st.subheader("🛡️ Defensive Wall")
    df_def = df[df['Category'] == 'Defensive'].copy()
    if not df_def.empty:
        st.dataframe(
            df_def.style.format({
                "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", 
                "Current Price": "${:.2f}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                "% P/L": format_pct, "Upside": "{:+.1%}", "Diff S1": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Sell Lv.1": "${:.0f}"
            }).map(color_pl, subset=['% P/L', 'Total Gain USD', 'Upside']),
            column_order=display_cols,
            column_config={
                "Total Cost": "Total Cost (USD)", 
                "% P/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)"
            },
            hide_index=True, use_container_width=True
        )

except Exception as e:
    st.error(f"Error: {e}")
