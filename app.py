import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ (เปลี่ยนชื่อ Page Title) ---
st.set_page_config(page_title="On The Moon Portfolio & Sniper Watchlist", page_icon="🌕", layout="wide")

# --- CSS ปรับแต่ง (Big Font Edition 🔍) ---
st.markdown("""
<style>
    /* ปรับขนาดฟอนต์พื้นฐาน */
    html, body, [class*="css"] { font-size: 1.1rem; }

    /* ตัวเลขการเงิน (Metrics) */
    [data-testid="stMetricValue"] { font-size: 3.2rem !important; font-weight: 900; }
    [data-testid="stMetricLabel"] { font-size: 1.3rem !important; }

    /* หัวข้อ (Headers) */
    h3 {
        padding-top: 1rem;
        border-bottom: 3px solid #444;
        padding-bottom: 0.5rem;
        font-size: 2.2rem !important;
    }

    /* Expander Text */
    .streamlit-expanderContent p, .streamlit-expanderContent li, .stMarkdown p {
        font-size: 1.2rem !important;
    }

    /* Table Width */
    div[data-testid="stDataFrame"] { width: 100%; }
    
    .stAlert { margin-top: 1rem; }
    
    /* Text Area Font */
    textarea { font-size: 1.1rem !important; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. Initialize Session State ---

# 2.1 Portfolio Data (VOO, TSM, V, AMZN, LLY, NVDA)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
        {"Ticker": "TSM",  "Category": "Growth",    "Avg Cost": 274.9960, "Qty": 0.1118198},
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "AMZN", "Category": "Growth",    "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "NVDA", "Category": "Growth",    "Avg Cost": 178.7260, "Qty": 0.3351499},
    ]

# 2.2 Watchlist Data
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        "AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", 
        "WBD", "AMD", "AVGO", "IREN", "RKLB", "UBER", "CDNS", "WM"
    ]

# 2.3 Weekly Note
if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**
    * **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ
* **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**
    * **Event:** งบ **Micron (MU)** 🚨 *Highlight*
    * ถ้า "ดีมานด์ AI ล้น" → **NVDA & TSM** พุ่ง 🚀
* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
    * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน"""

# --- 3. Sidebar Settings ---
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

# --- 4. Data Fetching ---
try:
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))

    @st.cache_data(ttl=60) 
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=True)
        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].copy() if len(tickers_list) > 1 else df_hist.copy()
                df_t = df_t.dropna()
                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                df_t['EMA50'] = df_t['Close'].ewm(span=50, adjust=False).mean()
                df_t['SMA20'] = df_t['Close'].rolling(window=20).mean()
                df_t['STD20'] = df_t['Close'].rolling(window=20).std()
                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": df_t['EMA50'].iloc[-1], "Sell1": (df_t['SMA20'] + (df_t['STD20'] * 2)).iloc[-1]
                }
            except: pass
        return data_dict

    market_data = get_realtime_data(all_tickers)

    # --- 5. Data Processing ---
    df = pd.DataFrame(st.session_state.portfolio)
    if not df.empty:
        df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
        df['Value USD'] = df['Qty'] * df['Current Price']
        df['Total Cost'] = df['Qty'] * df['Avg Cost']
        df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
        df['% P/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
        
        total_value = df['Value USD'].sum() + cash_balance_usd
        total_gain = df['Total Gain USD'].sum()
        total_invested = df['Total Cost'].sum()

    # --- 6. UI Display (เปลี่ยนชื่อหัวข้อหลักตรงนี้ครับ 🌕) ---
    st.title("🌕 On The Moon Portfolio & Sniper Watchlist") 
    st.caption(f"Last Update (BKK Time): {target_date_str}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*31.45:,.0f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}", "Ready to Sniper")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Invested: ${total_invested:,.0f}")
    c4.metric("🚀 Destination", "To The Moon", "Portfolio Updated")

    st.markdown("---")

    # ส่วนตาราง Portfolio
    st.subheader("🚀 On The Moon Portfolio (Holdings)")
    if not df.empty:
        st.dataframe(
            df.style.format({
                "Qty": "{:.6f}", "Avg Cost": "${:.2f}", "Current Price": "${:.2f}",
                "% P/L": "{:+.2%}", "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}"
            }),
            column_order=["Ticker", "Category", "Qty", "Avg Cost", "Current Price", "% P/L", "Value USD", "Total Gain USD"],
            hide_index=True, use_container_width=True
        )

    # ส่วนตาราง Watchlist
    st.subheader("🎯 Sniper Watchlist")
    # ... (ส่วนการแสดงผล Watchlist โค้ดส่วนที่เหลือคงเดิม)

except Exception as e:
    st.error(f"Error: {e}")
