import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ON The Moon Portfolio & Sniper Watchlist", page_icon="🔭", layout="wide")

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

# 2.1 Portfolio Data (อัปเดตใหม่ตามภาพ Dime! ล่าสุด)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        # Growth Engine
        {"Ticker": "AMZN", "Category": "Growth", "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "NVDA", "Category": "Growth", "Avg Cost": 178.7260, "Qty": 0.3351499},
        {"Ticker": "TSM",  "Category": "Growth", "Avg Cost": 274.9960, "Qty": 0.1118198},
        # Defensive Wall
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
    ]

# 2.2 Watchlist Data (เพิ่ม AAPL, PLTR กลับเข้า Watchlist เพราะไม่ได้ถือแล้ว)
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        "AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "SMH", "QQQ", "QQQM", "MU", "CRWD", "PATH",
        "RKLB", "ASTS", "EOSE", "IREN", "WBD", "CRWV", "UBER", "SCHD", "CDNS",
        "PG", "PM", "KO", "PEP", "MO", "NKE", "MNST", "MDLZ", "HSY", "EL", "KMB", "KVUE", "CL", "KHC", "CHD", 
        "MCD", "BKNG", "MAR", "HLT", "CMG", "TKO", "CCL", "EXPE", "CMCSA", "ABNB", "SBUX", "RCL", "LVS", "LYV", "FOX", "FOXA", "YUM", "CHTR", "DRI",
        "ORCL", "IBM", "INTU", "ACN", "NOW", "ADBE", "ADP", "SNPS", "CRM", "NFLX", "APP", "PANW", "FTNT", "EA", "TTD",
        "NEE", "SO", "VST", "EXC", "TRGP", "ED", "WEC", "PCG", "NRG", "ATO", "DTE", "XEL", "DUK", "SRE", "ETR", "AEE", "FE", "PPL", "CNP", "CEG", "AWK", "EIX", "NI", "LNT", "AEP", "D", "PEG", "ES", "CMS", "EVRG",
        "CAT", "DE", "TT", "MMM", "ITW", "LRCX", "ETN", "JCI", "AME", "ROK", "CARR", "AMAT", "GEV", "PH", "CMI", "PCAR",
        "NEM", "FCX", "MLM", "VMC", "NUE", "STLD",
        "BRK.B", "WFC", "C", "PGR", "WELL", "PLD", "CB", "KKR", "HOOD", "IBKR", "CME", "MMC", "ICE", "APO", "MS", "BX", "BLK", "GS", "SCHW", "BK", "AXP", "COF", "AON", "SPG", "JPM", "BAC",
        "ABBV", "TMO", "DHR", "GILD", "PFE", "BSX", "VRTX", "BMY", "MRK", "ISRG", "SYK", "EW", "GEHC", "DXCM", "BIIB", "STE", "JNJ", "ABT", "AMGN", "MDT"
    ]
    portfolio_tickers = [item['Ticker'] for item in st.session_state.portfolio]
    st.session_state.watchlist = list(set([x for x in st.session_state.watchlist if x not in portfolio_tickers]))

# 2.3 Weekly Note
if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
    * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน"""

# --- 3. Sidebar Management ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    # ปรับ Cash Flow ตามหน้าจอ Analytics ($0.00 หรือตามที่คุณมีจริง)
    cash_balance_usd = st.number_input("Cash Flow ($)", value=0.00, step=10.0, format="%.2f")
    st.divider()
    tab_add, tab_remove = st.tabs(["➕ Add Asset", "🗑️ Remove/Sell"])
    # (ระบบจัดการ Form คงเดิม...)

# --- 5. Data Fetching (FIXED: threads=False แก้โค้ดแดง) ---
try:
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))

    @st.cache_data(ttl=120, show_spinner="Fetching Real-time Market Data...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        try:
            # แก้ไขหลัก: threads=False เพื่อความเสถียรของ Streamlit Cloud
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=False, progress=False)
        except: return {}

        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                if df_t.empty or len(df_t) < 50: continue

                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rsi_val = 100 - (100 / (1 + (gain/loss).iloc[-1]))

                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi_val,
                    "Sell1": (df_t['Close'].rolling(window=20).mean() + (df_t['Close'].rolling(window=20).std() * 2)).iloc[-1],
                    "Sell2": df_t['Close'].iloc[-252:].max()
                }
            except: continue
        return data_dict

    if st.button('🔄 Refresh Data (Real-time)'):
        st.cache_data.clear()
        st.rerun()

    market_data = get_realtime_data(all_tickers)

    # --- 6. Data Processing & UI ---
    df = pd.DataFrame(st.session_state.portfolio)
    if not df.empty:
        df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
        df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
        df['Value USD'] = df['Qty'] * df['Current Price']
        df['Total Cost'] = df['Qty'] * df['Avg Cost']
        df['Gain USD'] = df['Value USD'] - df['Total Cost']
        df['% P/L'] = (df['Current Price'] - df['Avg Cost']) / df['Avg Cost']
        
        total_value = df['Value USD'].sum() + cash_balance_usd
        total_gain = df['Gain USD'].sum()
    else: total_value, total_gain = cash_balance_usd, 0

    # --- 8. UI Display ---
    st.title("🔭 ON The Moon Portfolio & Sniper Watchlist") 
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*31.45:,.0f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}", "Ready")
    c3.metric("📈 Unrealized G/L", f"${total_gain:+.2f}", f"{(total_gain/df['Total Cost'].sum()*100) if not df.empty else 0:.2f}%")
    c4.metric("📅 Last Sync", "Dime! 18 Dec", "Status: Active")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    def format_arrow(val): return f"{val:+.2%} {'⬆️' if val > 0 else '⬇️' if val < 0 else '➖'}"

    with col_left:
        for cat, icon in [("Growth", "🚀"), ("Defensive", "🛡️")]:
            st.subheader(f"{icon} {cat} Engine")
            d = df[df['Category'] == cat]
            if not d.empty:
                st.dataframe(d[['Ticker', 'Qty', 'Avg Cost', 'Current Price', '% P/L', 'Gain USD']].style.format({
                    "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Current Price": "${:.2f}", "% P/L": format_arrow, "Gain USD": "${:+.2f}"
                }), hide_index=True, use_container_width=True)

    with col_right:
        st.subheader("🎯 Sniper Watchlist")
        watch_data = []
        for t in sorted(list(set(st.session_state.watchlist))):
            d = market_data.get(t, {})
            p, b1 = d.get('Price', 0), d.get('EMA50', 0)
            diff = (p-b1)/b1 if b1 > 0 else 0
            watch_data.append({"Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": p, "Diff S1": diff, "RSI": d.get('RSI', 50)})
        st.dataframe(pd.DataFrame(watch_data).style.format({"Price": "${:.2f}", "Diff S1": "{:+.1%}", "RSI": "{:.0f}"}), hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"System Error: {e}")
