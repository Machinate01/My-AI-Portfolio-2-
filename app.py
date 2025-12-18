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

# 2.1 Portfolio Data (อิงตามพอร์ตจริงของคุณ)
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

# 2.2 Watchlist Data (รวมรายชื่อจาก Heatmap YTD ทั้งหมด)
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

# 2.3 Weekly Note Data
if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**
    * **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ
* **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**
    * **Event:** งบ **Micron (MU)** 🚨 *Highlight*
    * ถ้า "ดีมานด์ AI ล้น" → **NVDA & TSM** พุ่ง 🚀
* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
    * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน"""

# --- 3. Sidebar Management ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=0.00, step=10.0, format="%.2f")
    st.divider()
    tab_add, tab_remove = st.tabs(["➕ Add Asset", "🗑️ Remove/Sell"])
    with tab_add:
        st.subheader("Add to Portfolio")
        with st.form("add_port"):
            p_ticker = st.text_input("Ticker (e.g. MSFT)").upper()
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
                ticker_to_remove = to_remove.split(" ")[0]
                st.session_state.portfolio = [x for x in st.session_state.portfolio if x['Ticker'] != ticker_to_remove]
                st.rerun()

# --- 4. PRB Tier Mapping (Static) ---
prb_tiers = {
    "NVDA": "S+", "AAPL": "S+", "MSFT": "S+", "GOOGL": "S+", "TSM": "S+", "ASML": "S+",
    "AMD": "S", "PLTR": "S", "AMZN": "S", "META": "S", "AVGO": "S", "CRWD": "S", "SMH": "S", "QQQ": "ETF",
    "TSLA": "A+", "V": "A+", "MA": "A+", "LLY": "A+", "JNJ": "A+", "BRK.B": "A+", "PG": "B+", "KO": "B+",
    "NFLX": "A", "WM": "A", "WMT": "A", "CEG": "A", "NET": "A", "PANW": "A", "SCHD": "A", "CDNS": "S",
    "ISRG": "B+", "RKLB": "B+", "TMDX": "B+", "IREN": "B+", "MELI": "B+", "ASTS": "B+", "EOSE": "B+",
    "ADBE": "B", "UBER": "B", "HOOD": "B", "DASH": "B", "BABA": "B", "CRWV": "B", "MU": "B", "PATH": "C",
    "TTD": "C", "LULU": "C", "CMG": "C", "DUOL": "C", "PDD": "C", "ORCL": "C", "WBD": "Hold",
    "VOO": "ETF", "QQQM": "ETF"
}

# --- 5. Data Fetching (FIXED: threads=False) ---
try:
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    all_tickers = list(set([item['Ticker'] for item in st.session_state.portfolio] + st.session_state.watchlist))

    @st.cache_data(ttl=120, show_spinner="Fetching Real-time Market Data...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        if not tickers_list: return {}
        try:
            # แก้ไขหลัก: ใช้ threads=False เพื่อเลี่ยง Error 'can't start new thread'
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=False, progress=False)
        except Exception as e:
            st.error(f"Data Download Error: {e}")
            return {}

        for ticker in tickers_list:
            try:
                # ตรวจสอบโครงสร้าง DataFrame
                df_t = df_hist[ticker].dropna() if len(tickers_list) > 1 else df_hist.dropna()
                
                if df_t.empty or len(df_t) < 200:
                    data_dict[ticker] = {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0, "Sell2": 0}
                    continue

                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs.iloc[-1]))

                sma20 = df_t['Close'].rolling(window=20).mean()
                std20 = df_t['Close'].rolling(window=20).std()
                sell_r1 = (sma20 + (std20 * 2)).iloc[-1] 
                sell_r2 = df_t['Close'].iloc[-252:].max()

                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi_val, "Sell1": sell_r1, "Sell2": sell_r2
                }
            except:
                data_dict[ticker] = {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0, "Sell2": 0}
        return data_dict

    if st.button('🔄 Refresh Data (Real-time)'):
        st.cache_data.clear()
        st.rerun()

    market_data = get_realtime_data(all_tickers)

    # --- 6. Data Processing ---
    df = pd.DataFrame(st.session_state.portfolio)
    if not df.empty:
        df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
        df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
        df['Value USD'] = df['Qty'] * df['Current Price']
        df['Total Cost'] = df['Qty'] * df['Avg Cost']
        df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
        df['% P/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
        df['Day Change USD'] = (df['Current Price'] - df['PrevClose']) * df['Qty']
        
        def get_levels_series(ticker, price):
            data = market_data.get(ticker, {})
            b1, b2, s1, s2 = data.get('EMA50', 0), data.get('EMA200', 0), data.get('Sell1', 0), data.get('Sell2', 0)
            return pd.Series([b1, b2, s1, s2, (price-b1)/b1 if b1>0 else 0, (s1-price)/price if price>0 else 0], 
                            index=['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2', 'Diff S1', 'Upside'])

        df = pd.concat([df, df.apply(lambda x: get_levels_series(x['Ticker'], x['Current Price']), axis=1)], axis=1)
        total_value = df['Value USD'].sum() + cash_balance_usd
        total_gain = df['Total Gain USD'].sum()
        total_day_change = df['Day Change USD'].sum()
        total_invested = df['Total Cost'].sum()
    else:
        total_value, total_gain, total_day_change, total_invested = cash_balance_usd, 0, 0, 0

    # --- 7. UI Display ---
    st.title("🔭 ON The Moon Portfolio & Sniper Watchlist") 
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*31.43:,.0f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}", "Ready to Sniper")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Invested: ${total_invested:,.0f}")
    c4.metric("📅 Day Change", f"${total_day_change:+.2f}", f"{(total_day_change/total_invested*100) if total_invested else 0:+.2f}%")

    st.markdown("---")
    col_mid_left, col_mid_right = st.columns([2, 1])
    with col_mid_left:
        st.subheader("ℹ️ Info") 
        with st.expander("📅 Weekly Analysis & Notes", expanded=True):
            st.markdown(st.session_state.weekly_note)

    with col_mid_right:
        st.subheader("📊 Allocation")
        if not df.empty:
            fig = go.Figure(data=[go.Pie(labels=list(df['Ticker'])+['CASH'], values=list(df['Value USD'])+[cash_balance_usd], hole=.5)])
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col_bot_left, col_bot_right = st.columns(2) 

    def format_arrow(val): return f"{val:+.2%} {'⬆️' if val > 0 else '⬇️' if val < 0 else '➖'}"
    def color_diff(val): return 'color: #28a745; font-weight: bold;' if val < 0 else 'color: #90EE90;' if 0<=val<=0.02 else 'color: #dc3545;'

    with col_bot_left:
        for cat, icon in [("Growth", "🚀"), ("Defensive", "🛡️")]:
            st.subheader(f"{icon} {cat} Engine")
            if not df.empty:
                d = df[df['Category'] == cat]
                st.dataframe(d.style.format({"Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Current Price": "${:.2f}", "% P/L": format_arrow, "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}", "Diff S1": "{:+.1%}"}).map(color_diff, subset=['Diff S1']), hide_index=True)

    with col_bot_right:
        st.subheader("🎯 Sniper Watchlist")
        watch_data = []
        for t in sorted(list(set(st.session_state.watchlist))):
            d = market_data.get(t, {})
            p, b1, s1 = d.get('Price', 0), d.get('EMA50', 0), d.get('Sell1', 0)
            diff = (p-b1)/b1 if b1 > 0 else 9.99
            sig = "1. ✅ IN ZONE" if diff < 0 and p > 0 else "2. 🟢 ALERT" if 0 <= diff <= 0.02 else "5. 🔴 PROFIT" if p >= s1 and p > 0 else "3. ➖ Wait"
            watch_data.append({"Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": p, "Signal": sig.split(". ")[1], "Diff S1": diff, "RSI": d.get('RSI', 50)})
        st.dataframe(pd.DataFrame(watch_data).style.format({"Price": "${:.2f}", "Diff S1": "{:+.1%}", "RSI": "{:.0f}"}).map(color_diff, subset=['Diff S1']), hide_index=True)

except Exception as e:
    st.error(f"System Error: {e}")
