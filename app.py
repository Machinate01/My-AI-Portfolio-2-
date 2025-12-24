import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- CONFIGURATION (Magic Numbers - KISS Principle) ---
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
REFRESH_RATE_SEC = 60  # ปรับให้ถี่ขึ้นเพื่อแก้ปัญหาข้อมูลไม่อัปเดต

# --- 1. SETUP PAGE ---
st.set_page_config(page_title="My Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

# คงเดิม: CSS ปรับแต่ง UI
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }
    h3 { padding-top: 1rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 2.2rem !important; }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. INITIALIZE STATE ---
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
    st.session_state.watchlist = ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "CDNS", "UBER", "IREN", "WM"]

# --- 3. CORE LOGIC (SRP & Meaningful Names) ---

@st.cache_data(ttl=REFRESH_RATE_SEC)
def fetch_market_data(tickers):
    """ดึงข้อมูลราคาหุ้นและคำนวณค่าทางเทคนิค (แยกส่วนเพื่อความคลีน)"""
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="2y", group_by='ticker', auto_adjust=True)
        market_summary = {}
        for ticker in tickers:
            try:
                # จัดการโครงสร้างข้อมูลของ yfinance
                ticker_df = raw_data[ticker].dropna() if len(tickers) > 1 else raw_data.dropna()
                if ticker_df.empty: continue

                # คำนวณค่าต่างๆ
                close_prices = ticker_df['Close']
                current_price = close_prices.iloc[-1]
                
                ema50 = close_prices.ewm(span=EMA_FAST, adjust=False).mean().iloc[-1]
                ema200 = close_prices.ewm(span=EMA_SLOW, adjust=False).mean().iloc[-1]
                
                # สูตร RSI แบบมาตรฐาน
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
                rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]

                market_summary[ticker] = {
                    "Price": current_price,
                    "PrevClose": close_prices.iloc[-2],
                    "EMA50": ema50,
                    "EMA200": ema200,
                    "RSI": rsi,
                    "Sell1": (close_prices.rolling(20).mean() + (close_prices.rolling(20).std() * 2)).iloc[-1]
                }
            except: continue
        return market_summary
    except: return {}

def apply_row_styles(row):
    """จัดการสี Price และ Value ตามกำไร/ขาดทุน (DRY Principle)"""
    color = '#28a745' if row['Total Gain ($)'] >= 0 else '#dc3545'
    return [f'color: {color}' if col in ['Price', 'Value ($)'] else '' for col in row.index]

# --- 4. UI COMPONENTS ---

def render_portfolio_table(data_df, title):
    """ฟังก์ชันวาดตารางพอร์ต (DRY: ใช้ร่วมกันทั้ง Growth/Defensive)"""
    st.subheader(title)
    if data_df.empty:
        st.info("No assets in this category.")
        return

    # ลำดับคอลัมน์ตามความต้องการเดิม
    col_order = ["Ticker", "Qty", "Avg Cost", "Total Cost ($)", "% Total", "Price", "Value ($)", "Total Gain ($)", "Upside", "Diff S1", "Buy Lv.1", "Buy Lv.2"]
    
    st.dataframe(
        data_df.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost ($)": "${:,.2f}", "Price": "${:.2f}",
            "Value ($)": "${:,.2f}", "Total Gain ($)": "${:,.2f}", "Diff S1": "{:+.1%}", 
            "% Total": "{:+.2%}", "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"
        })
        .map(lambda x: 'color: #28a745' if x >= 0 else 'color: #dc3545', subset=['% Total', 'Total Gain ($)', 'Upside'])
        .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1'])
        .apply(apply_row_styles, axis=1),
        column_order=col_order,
        hide_index=True, use_container_width=True
    )

# --- 5. MAIN APP ---

# ส่วนจัดการปุ่ม Refresh เพื่อแก้ปัญหาข้อมูลไม่อัปเดต
if st.sidebar.button('🔄 Force Refresh Data'):
    st.cache_data.clear()
    st.rerun()

cash_balance = st.sidebar.number_input("Cash Flow ($)", value=400.0, step=10.0)

all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))
market_data = fetch_market_data(all_tickers)

# ประมวลผลข้อมูลลง DataFrame
portfolio_df = pd.DataFrame(st.session_state.portfolio)
if not portfolio_df.empty:
    portfolio_df['Price'] = portfolio_df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    portfolio_df['Total Cost ($)'] = portfolio_df['Qty'] * portfolio_df['Avg Cost']
    portfolio_df['Value ($)'] = portfolio_df['Qty'] * portfolio_df['Price']
    portfolio_df['Total Gain ($)'] = portfolio_df['Value ($)'] - portfolio_df['Total Cost ($)']
    portfolio_df['% Total'] = (portfolio_df['Price'] - portfolio_df['Avg Cost']) / portfolio_df['Avg Cost']
    portfolio_df['Buy Lv.1'] = portfolio_df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA50', 0))
    portfolio_df['Buy Lv.2'] = portfolio_df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA200', 0))
    portfolio_df['Diff S1'] = (portfolio_df['Price'] - portfolio_df['Buy Lv.1']) / portfolio_df['Buy Lv.1']
    portfolio_df['Upside'] = (portfolio_df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Sell1', 0)) - portfolio_df['Price']) / portfolio_df['Price']

# สรุปผล Metrics
st.title("🔭 My Portfolio & Sniper Watchlist")
total_port_val = portfolio_df['Value ($)'].sum() + cash_balance
total_gain = portfolio_df['Total Gain ($)'].sum()

c1, c2, c3 = st.columns(3)
c1.metric("💰 Total Portfolio Value", f"${total_port_val:,.2f}")
c2.metric("🌊 Cash Available", f"${cash_balance:,.2f}")
c3.metric("📈 Unrealized P/L", f"${total_gain:,.2f}")

st.markdown("---")

# แบ่งหน้ากระดาษตามเดิม
col_left, col_right = st.columns(2)

with col_left:
    render_portfolio_table(portfolio_df[portfolio_df['Category'] == 'Growth'], "🚀 Growth Engine")
    render_portfolio_table(portfolio_df[portfolio_df['Category'] == 'Defensive'], "🛡️ Defensive Wall")

with col_right:
    st.subheader("🎯 Sniper Watchlist")
    watchlist_results = []
    for ticker in sorted(st.session_state.watchlist):
        stock_info = market_data.get(ticker, {})
        price = stock_info.get('Price', 0)
        ema50 = stock_info.get('EMA50', 0)
        diff = (price - ema50) / ema50 if ema50 > 0 else 9.99
        
        status = "1. ✅ IN ZONE" if diff < 0 else "2. 🟢 ALERT" if diff < 0.02 else "3. ➖ Wait"
        watchlist_results.append({
            "Signal": status, "Ticker": ticker, "Price": price, "Diff S1": diff, 
            "RSI": stock_info.get('RSI', 50), "Buy Lv.1": ema50, "Buy Lv.2": stock_info.get('EMA200', 0)
        })
    
    watchlist_df = pd.DataFrame(watchlist_results).sort_values(["Signal", "Diff S1"])
    st.dataframe(
        watchlist_df.style.format({"Price": "${:.2f}", "Diff S1": "{:+.1%}", "RSI": "{:.0f}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"})
        .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1']),
        hide_index=True, use_container_width=True
    )
