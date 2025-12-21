import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- CONFIGURATION (Magic Numbers) ---
# ตั้งค่าตัวแปรที่นี่ที่เดียว (Easy to maintain)
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
BB_STD_DEV = 2.0
BB_WINDOW = 20
REFRESH_RATE = 300  # seconds

# --- 1. SETUP PAGE ---
st.set_page_config(page_title="My Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

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
    st.session_state.watchlist = ["AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "WBD", "AMD", "AVGO", "IREN", "RKLB", "UBER", "CDNS", "WM"]

if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันอังคาร 16 ธ.ค.:** ติดตาม Retail Sales\n* **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ\n* **วันพุธ 17 ธ.ค.:** งบ Micron (MU) 🚨 Highlight AI Hardware\n* **วันพฤหัส 18 ธ.ค.:** เงินเฟ้อ CPI > 3.1% Tech อาจย่อ"""

# --- 3. HELPER FUNCTIONS (SRP & DRY) ---

@st.cache_data(ttl=REFRESH_RATE)
def fetch_stock_data(tickers_list):
    """
    ดึงข้อมูลราคาหุ้นดิบจาก Yahoo Finance (แยกส่วน Fetch เพื่อ Clean Code)
    """
    if not tickers_list:
        return {}
    try:
        # Download ทีเดียวเพื่อความเร็ว (Vectorization)
        return yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=True)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}

def calculate_technical_indicators(df):
    """
    คำนวณ Indicator ทางเทคนิค (EMA, RSI, Bollinger Bands)
    """
    if df.empty:
        return {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0}

    try:
        # Price Data
        current_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]

        # EMA Calculation
        ema_fast = df['Close'].ewm(span=EMA_FAST, adjust=False).mean().iloc[-1]
        ema_slow = df['Close'].ewm(span=EMA_SLOW, adjust=False).mean().iloc[-1]

        # RSI Calculation (Explicit Logic for readability)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # Bollinger Bands (Upper Band as Sell Level 1)
        sma = df['Close'].rolling(window=BB_WINDOW).mean()
        std = df['Close'].rolling(window=BB_WINDOW).std()
        sell_level_1 = (sma + (std * BB_STD_DEV)).iloc[-1]

        return {
            "Price": current_price,
            "PrevClose": prev_close,
            "EMA50": ema_fast,
            "EMA200": ema_slow,
            "RSI": current_rsi,
            "Sell1": sell_level_1
        }
    except:
        return {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0}

def get_processed_market_data(tickers):
    """
    Orchestrator function: ดึงข้อมูล -> คำนวณ -> ส่งคืน Dictionary
    """
    raw_data = fetch_stock_data(tickers)
    processed_data = {}
    
    for ticker in tickers:
        try:
            # Handle Single vs Multiple Ticker structure from yfinance
            df_t = raw_data[ticker].dropna() if len(tickers) > 1 else raw_data.dropna()
            processed_data[ticker] = calculate_technical_indicators(df_t)
        except:
            processed_data[ticker] = calculate_technical_indicators(pd.DataFrame())
            
    return processed_data

# --- 4. STYLING FUNCTIONS (DRY) ---

def style_portfolio_rows(row):
    """Colorize Value and Price based on Profit/Loss"""
    color = '#28a745' if row['Total Gain USD'] >= 0 else '#dc3545'
    return [f'color: {color}' if col in ['Value USD', 'Current Price'] else '' for col in row.index]

def highlight_sniper_zone(s):
    """Highlight rows based on Sniper Signal"""
    if "IN ZONE" in str(s['Signal']): return ['background-color: rgba(40, 167, 69, 0.4)'] * len(s)
    if "ALERT" in str(s['Signal']): return ['background-color: rgba(40, 167, 69, 0.2)'] * len(s)
    return [''] * len(s)

def get_common_column_config():
    """Configuration สำหรับตาราง Portfolio (ใช้ซ้ำได้)"""
    return {
        "Current Price": "Price",
        "Total Cost": "Total Cost ($)", 
        "% P/L": "% Total", 
        "Value USD": "Value ($)", 
        "Total Gain USD": "Total Gain ($)", 
        "Buy Lv.2": "Buy Lv.2"
    }

# --- 5. MAIN APP LOGIC ---

# Sidebar
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
                    if p_ticker in st.session_state.watchlist: st.session_state.watchlist.remove(p_ticker)
                    st.rerun()

    with tab_remove:
        st.subheader("Sell / Remove Position")
        current_holdings = [f"{item['Ticker']} ({item['Category']})" for item in st.session_state.portfolio]
        if current_holdings:
            to_remove = st.selectbox("Select Position to Remove", current_holdings)
            if st.button("🗑️ Confirm Remove Position"):
                t_rem = to_remove.split(" ")[0]
                st.session_state.portfolio = [x for x in st.session_state.portfolio if x['Ticker'] != t_rem]
                st.warning(f"Removed {t_rem}")
                st.rerun()

# Data Processing
try:
    port_tickers = [item['Ticker'] for item in st.session_state.portfolio]
    all_tickers = list(set(port_tickers + st.session_state.watchlist))
    
    if st.button('🔄 Refresh Data (Real-time)'): 
        st.cache_data.clear()
        st.rerun()
        
    market_data = get_processed_market_data(all_tickers)

    # Prepare Portfolio DataFrame
    df = pd.DataFrame(st.session_state.portfolio)
    
    if not df.empty:
        # Map Market Data
        df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
        df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
        
        # Calculate Financials
        df['Value USD'] = df['Qty'] * df['Current Price']
        df['Total Cost'] = df['Qty'] * df['Avg Cost']
        df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
        df['% P/L'] = (df['Current Price'] - df['Avg Cost']) / df['Avg Cost']
        df['Day Change USD'] = (df['Current Price'] - df['PrevClose']) * df['Qty']
        
        # Calculate Technical Levels (Vectorized logic not needed for simple lookup)
        df['Buy Lv.1'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA50', 0))
        df['Buy Lv.2'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('EMA200', 0))
        df['Sell Lv.1'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Sell1', 0))
        
        # Calculate Signals
        df['Diff S1'] = (df['Current Price'] - df['Buy Lv.1']) / df['Buy Lv.1']
        df['Upside'] = (df['Sell Lv.1'] - df['Current Price']) / df['Current Price']

        # Summaries
        total_value = df['Value USD'].sum() + cash_balance_usd
        total_gain = df['Total Gain USD'].sum()
        total_day_change = df['Day Change USD'].sum()
        total_invested = df['Total Cost'].sum()
    else:
        total_value = cash_balance_usd; total_gain = 0; total_day_change = 0; total_invested = 0

    # UI Layout
    st.title("🔭 My Portfolio & Sniper Watchlist")
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value", f"${total_value:,.2f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Inv: ${total_invested:,.0f}")
    c4.metric("📅 Day Change", f"${total_day_change:+.2f}")
    
    st.markdown("---")

    # Middle Section
    col_mid_left, col_mid_right = st.columns([2, 1])
    with col_mid_left:
        with st.expander("📅 Weekly Analysis & Notes", expanded=True): 
            st.markdown(st.session_state.weekly_note)
    with col_mid_right:
        if not df.empty:
            fig = go.Figure(data=[go.Pie(labels=list(df['Ticker']) + ['CASH'], values=list(df['Value USD']) + [cash_balance_usd], hole=.5)])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # Portfolio Tables
    col_bot_left, col_bot_right = st.columns(2)
    
    port_cols = ["Ticker", "Qty", "Avg Cost", "Total Cost", "% P/L", "Current Price", "Value USD", "Total Gain USD", "Upside", "Diff S1", "Buy Lv.1", "Buy Lv.2"]
    
    with col_bot_left:
        # Growth Table
        st.subheader("🚀 Growth Engine")
        if not df.empty:
            df_g = df[df['Category'] == 'Growth'].copy()
            st.dataframe(
                df_g.style.format({
                    "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                    "Diff S1": "{:+.1%}", "% P/L": "{:+.2%}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                    "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"
                })
                .map(lambda x: 'color: #28a745' if x >= 0 else 'color: #dc3545', subset=['% P/L', 'Total Gain USD', 'Upside'])
                .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1'])
                .apply(style_portfolio_rows, axis=1),
                column_order=port_cols,
                column_config=get_common_column_config(),
                hide_index=True, use_container_width=True
            )

        # Defensive Table
        st.subheader("🛡️ Defensive Wall")
        if not df.empty:
            df_d = df[df['Category'] == 'Defensive'].copy()
            st.dataframe(
                df_d.style.format({
                    "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                    "Diff S1": "{:+.1%}", "% P/L": "{:+.2%}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                    "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"
                })
                .map(lambda x: 'color: #28a745' if x >= 0 else 'color: #dc3545', subset=['% P/L', 'Total Gain USD', 'Upside'])
                .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1'])
                .apply(style_portfolio_rows, axis=1),
                column_order=port_cols,
                column_config=get_common_column_config(),
                hide_index=True, use_container_width=True
            )

    # Watchlist Table
    with col_bot_right:
        st.subheader("🎯 Sniper Watchlist")
        wl_data = []
        for t in sorted(st.session_state.watchlist):
            d = market_data.get(t, {})
            price = d.get('Price', 0); buy1 = d.get('EMA50', 0); buy2 = d.get('EMA200', 0)
            diff_s1 = (price - buy1)/buy1 if buy1 > 0 else 9.99
            
            # Logic: Signal Determination
            if diff_s1 < 0: signal = "1. ✅ IN ZONE"
            elif diff_s1 < 0.02: signal = "2. 🟢 ALERT"
            else: signal = "3. ➖ Wait"
            
            wl_data.append({
                "Ticker": t, "Price": price, "Signal": signal, 
                "Diff S1": diff_s1, "RSI": d.get('RSI', 50), 
                "Buy Lv.1": buy1, "Buy Lv.2": buy2
            })
        
        df_w = pd.DataFrame(wl_data)
        if not df_w.empty:
            df_w = df_w.sort_values(["Signal", "Diff S1"])
            st.dataframe(
                df_w.style.format({"Price": "${:.2f}", "Diff S1": "{:+.1%}", "RSI": "{:.0f}", "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}"})
                .apply(highlight_sniper_zone, axis=1)
                .map(lambda x: 'color: #28a745; font-weight: bold;' if x < 0 else ('color: #90EE90;' if x <= 0.02 else 'color: #dc3545;'), subset=['Diff S1']),
                column_order=["Signal", "Ticker", "Price", "Diff S1", "RSI", "Buy Lv.1", "Buy Lv.2"],
                hide_index=True, use_container_width=True
            )

except Exception as e:
    st.error(f"System Error: {e}")
