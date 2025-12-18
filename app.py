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

if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
    * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน"""

# --- 3. Sidebar Management ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=0.00, step=10.0, format="%.2f")
    st.divider()
    tab_add, tab_remove = st.tabs(["➕ Add Asset", "🗑️ Remove/Sell"])
    # (โค้ดส่วน Add/Remove คงเดิม...)

# --- 5. Data Fetching (FIXED: แก้โค้ดแดง) ---
try:
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")
    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))

    @st.cache_data(ttl=120, show_spinner="Fetching Real-time Market Data...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        try:
            # แก้ไขหลัก: threads=False ป้องกัน Error can't start new thread
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=False, progress=False)
        except Exception as e:
            st.error(f"Data Download Error: {e}")
            return {}

        for ticker in tickers_list:
            try:
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                if df_t.empty: continue

                # ค้นหาราคาและค่าทางเทคนิค
                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                
                # RSI 14
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs.iloc[-1]))

                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi_val,
                    "Sell1": (df_t['Close'].rolling(window=20).mean() + (df_t['Close'].rolling(window=20).std() * 2)).iloc[-1],
                    "Sell2": df_t['Close'].iloc[-252:].max()
                }
            except:
                continue
        return data_dict

    if st.button('🔄 Refresh Data (Real-time)'):
        st.cache_data.clear()
        st.rerun()

    market_data = get_realtime_data(all_tickers)

    # --- 6. UI Rendering ---
    # (ใช้ตรรกะการคำนวณและแสดงผลเดิมของคุณทั้งหมด...)
    st.title("🔭 ON The Moon Portfolio & Sniper Watchlist")
    # ... สรุปภาพรวมและตารางพอร์ต ...
