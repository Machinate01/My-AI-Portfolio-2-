import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ (ต้องอยู่บรรทัดแรกสุด!) ---
st.set_page_config(page_title="My Portfolio & Watchlist", page_icon="🔭", layout="wide")

# CSS ปรับแต่ง
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2.0rem !important; font-weight: 800; }
    h3 { padding-top: 0.5rem; border-bottom: 2px solid #444; padding-bottom: 0.5rem; font-size: 1.4rem !important; }
    .stAlert { margin-top: 1rem; }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. ข้อมูลพอร์ต (Portfolio Setup) ---
# คุณสามารถแก้ไขจำนวนหุ้น (Qty) และต้นทุน (Avg Cost) ได้ที่นี่
try:
    cash_balance_usd = 90.00 
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    # 2.1 พอร์ตหลัก (Hardcoded Holdings)
    my_portfolio_data = [
        {"Ticker": "AMZN", "Company": "Amazon.com Inc.",       "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "V",    "Company": "Visa Inc.",             "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "LLY",  "Company": "Eli Lilly and Company", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "NVDA", "Company": "NVIDIA Corp.",          "Avg Cost": 178.7260, "Qty": 0.3351499},
        {"Ticker": "VOO",  "Company": "Vanguard S&P 500 ETF",  "Avg Cost": 628.1220, "Qty": 0.0614849},
        {"Ticker": "TSM",  "Company": "Taiwan Semiconductor",  "Avg Cost": 274.9960, "Qty": 0.1118198},
    ]

    # 2.2 Watchlist Tickers
    my_watchlist_tickers = [
        "AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "SMH", "QQQ", "QQQM", "MU", "CRWD", "PATH",
        "RKLB", "ASTS", "EOSE", "IREN", "WBD", "CRWV", "KO", "PG", "WM", "UBER", "SCHD"
    ] 

    # รวม Ticker ทั้งหมดเพื่อดึงข้อมูลทีเดียว
    port_tickers = [item['Ticker'] for item in my_portfolio_data]
    all_tickers = list(set(port_tickers + my_watchlist_tickers))

    # PRB Tier Mapping (Static)
    prb_tiers = {
        "NVDA": "S+", "AAPL": "S+", "MSFT": "S+", "GOOGL": "S+", "TSM": "S+", "ASML": "S+",
        "AMD": "S", "PLTR": "S", "AMZN": "S", "META": "S", "AVGO": "S", "CRWD": "S", "SMH": "S", "QQQ": "ETF",
        "TSLA": "A+", "V": "A+", "MA": "A+", "LLY": "A+", "JNJ": "A+", "BRK.B": "A+", "PG": "B+", "KO": "B+",
        "NFLX": "A", "WM": "A", "WMT": "A", "CEG": "A", "NET": "A", "PANW": "A", "SCHD": "A",
        "ISRG": "B+", "RKLB": "B+", "TMDX": "B+", "IREN": "B+", "MELI": "B+", "ASTS": "B+", "EOSE": "B+",
        "ADBE": "B", "UBER": "B", "HOOD": "B", "DASH": "B", "BABA": "B", "CRWV": "B", "MU": "B", "PATH": "C",
        "TTD": "C", "LULU": "C", "CMG": "C", "DUOL": "C", "PDD": "C", "ORCL": "C", "WBD": "Hold",
        "VOO": "ETF", "QQQM": "ETF"
    }

    # --- 3. ฟังก์ชันดึงราคาและคำนวณ Technical (Yahoo Finance Engine) ---
    @st.cache_data(ttl=15, show_spinner="Fetching Real-time Data & Calculating EMA/RSI...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        
        # Download data for all tickers at once (Efficient)
        # Fetch 1 year history to calculate EMA200
        try:
            df_hist = yf.download(tickers_list, period="1y", group_by='ticker', auto_adjust=True, threads=True)
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            return {}

        for ticker in tickers_list:
            try:
                # Handle Multi-index or Single index
                if len(tickers_list) > 1:
                    df_t = df_hist[ticker].copy()
                else:
                    df_t = df_hist.copy()

                # Clean data
                df_t = df_t.dropna()
                
                if df_t.empty:
                    continue

                # Current Price & Prev Close
                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                
                # --- Technical Analysis Calculation ---
                # 1. EMA 50 & 200
                df_t['EMA50'] = df_t['Close'].ewm(span=50, adjust=False).mean()
                df_t['EMA200'] = df_t['Close'].ewm(span=200, adjust=False).mean()
                
                ema50 = df_t['EMA50'].iloc[-1]
                ema200 = df_t['EMA200'].iloc[-1]

                # 2. RSI (14)
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_t['RSI'] = 100 - (100 / (1 + rs))
                rsi_val = df_t['RSI'].iloc[-1]

                # 3. Dynamic Sell Levels
                # Sell 1: Upper Bollinger Band (20, 2) -> Short term resistance
                df_t['SMA20'] = df_t['Close'].rolling(window=20).mean()
                df_t['STD20'] = df_t['Close'].rolling(window=20).std()
                sell_r1 = (df_t['SMA20'] + (df_t['STD20'] * 2)).iloc[-1]
                
                # Sell 2: 52-Week High (Long term resistance)
                sell_r2 = df_t['Close'].max()

                # Store Data
                data_dict[ticker] = {
                    "Price": current_price,
                    "PrevClose": prev_close,
                    "EMA50": ema50,
                    "EMA200": ema200,
                    "RSI": rsi_val,
                    "Sell1": sell_r1,
                    "Sell2": sell_r2
                }
            except Exception as e:
                # Fallback for stocks with insufficient data (e.g. IPOs)
                data_dict[ticker] = {
                    "Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0, "Sell2": 0
                }
                
        return data_dict

    # Fetch Data
    market_data = get_realtime_data(all_tickers)

    # --- 4. คำนวณพอร์ต (Processing) ---
    df = pd.DataFrame(my_portfolio_data)
    
    # Map Real-time Data to Portfolio
    df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
    
    df['Value USD'] = df['Qty'] * df['Current Price']
    df['Total Cost'] = df['Qty'] * df['Avg Cost']
    df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
    df['%G/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
    
    # Map Technical Levels (Buy1=EMA50, Buy2=EMA200, Sell1=BB_Upper, Sell2=52W_High)
    def get_tech_cols(ticker):
        data = market_data.get(ticker, {})
        return pd.Series([
            data.get('EMA50', 0), data.get('EMA200', 0), 
            data.get('Sell1', 0), data.get('Sell2', 0),
            data.get('RSI', 50)
        ], index=['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2', 'RSI'])

    tech_cols = df['Ticker'].apply(get_tech_cols)
    df = pd.concat([df, tech_cols], axis=1)

    # Calculate Diff S1 (Distance to EMA 50)
    df['Diff S1'] = df.apply(lambda x: (x['Current Price'] - x['Buy Lv.1'])/x['Buy Lv.1'] if x['Buy Lv.1']>0 else 0, axis=1)

    total_value = df['Value USD'].sum() + cash_balance_usd
    total_gain = df['Total Gain USD'].sum()

    # --- 5. แสดงผล (UI) ---
    st.title("🔭 Sniper Portfolio & Watchlist (Real-time)") 
    st.caption(f"Last Update (BKK Time): {target_date_str} | Data Source: Yahoo Finance")

    # Scorecard
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value", f"${total_value:,.2f}")
    c2.metric("🌊 Cash Pool", f"${cash_balance_usd:,.2f}", "Ready")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}")
    c4.metric("📊 Market Status", "LIVE", "Auto Refresh")

    st.markdown("---")

    # Strategy Section
    c_mid_L, c_mid_R = st.columns([2, 1])
    with c_mid_L:
        with st.expander("🧠 Strategy: Nasdaq 24/5 & EMA Indicators", expanded=True):
            st.markdown("""
            * **📊 Dynamic Indicators (Live Calculation):**
                * **Buy Lv.1 (EMA 50):** เส้นค่าเฉลี่ย 50 วัน (เทรนด์ระยะกลาง) -> **จุด Sniper**
                * **Buy Lv.2 (EMA 200):** เส้นค่าเฉลี่ย 200 วัน (ฐานระยะยาว) -> **จุด Floor**
                * **Sell Lv.1:** Upper Bollinger Band (แนวต้านระยะสั้น)
                * **Sell Lv.2:** 52-Week High (จุดสูงสุดในรอบปี)
            * **🌊 Action:** ใช้เงินสด $90 รอช้อนเมื่อ **Diff S1 ติดลบ** (ราคาต่ำกว่า EMA50)
            """)
    with c_mid_R:
        labels = list(df['Ticker']) + ['CASH']
        values = list(df['Value USD']) + [cash_balance_usd]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, textinfo='label+percent')])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Main Portfolio & Watchlist (Split 50:50)
    col_left, col_right = st.columns(2)

    # --- LEFT: Growth & Defensive ---
    with col_left:
        def style_df(dframe):
            return dframe.style.format({
                "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}", "Diff S1": "{:+.1%}", "%G/L": "{:+.2%}",
                "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
            }).map(lambda v: 'color: #28a745' if v > 0 else 'color: #dc3545', subset=['Total Gain USD', '%G/L'])\
              .map(lambda v: 'color: #28a745; font-weight: bold' if v <= 0.02 else '', subset=['Diff S1'])

        st.subheader("🚀 Growth Engine")
        growth_tickers = ["NVDA", "TSM", "AMZN"]
        df_growth = df[df['Ticker'].isin(growth_tickers)].copy()
        st.dataframe(
            style_df(df_growth),
            column_order=["Ticker", "Qty", "Avg Cost", "Total Cost", "Current Price", "Value USD", "Diff S1", "Buy Lv.1", "Buy Lv.2"],
            hide_index=True, use_container_width=True
        )

        st.subheader("🛡️ Defensive Wall")
        def_tickers = ["V", "LLY", "VOO"]
        df_def = df[df['Ticker'].isin(def_tickers)].copy()
        st.dataframe(
            style_df(df_def),
            column_order=["Ticker", "Qty", "Avg Cost", "Total Cost", "Current Price", "Value USD", "Diff S1", "Buy Lv.1", "Buy Lv.2"],
            hide_index=True, use_container_width=True
        )

    # --- RIGHT: Watchlist (Dynamic) ---
    with col_right:
        st.subheader("🎯 Sniper Watchlist (Live)")
        
        watch_data = []
        for t in sorted(list(set(my_watchlist_tickers))):
            data = market_data.get(t, {})
            price = data.get('Price', 0)
            
            # Get Dynamic Levels
            buy1 = data.get('EMA50', 0)
            buy2 = data.get('EMA200', 0)
            sell1 = data.get('Sell1', 0)
            sell2 = data.get('Sell2', 0)
            rsi = data.get('RSI', 50)
            
            # Logic Calculation
            diff_s1 = (price - buy1)/buy1 if buy1 > 0 else 0
            
            signal = "Wait"
            if price <= buy1 and price > 0: signal = "✅ BUY"
            elif diff_s1 <= 0.02 and price > 0: signal = "🟢 ALERT"
            elif price >= sell1: signal = "🔴 PROFIT"
            
            watch_data.append({
                "Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": price, 
                "Signal": signal, "Diff S1": diff_s1, "RSI": rsi,
                "Buy Lv.1": buy1, "Buy Lv.2": buy2, "Sell Lv.1": sell1, "Sell Lv.2": sell2
            })
            
        df_watch = pd.DataFrame(watch_data).sort_values("Diff S1")
        
        st.dataframe(
            df_watch.style.format({
                "Price": "${:.2f}", "Diff S1": "{:+.1%}", "RSI": "{:.0f}",
                "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
            }).map(lambda v: 'background-color: #28a74544' if v == "✅ BUY" else ('background-color: #28a74522' if v == "🟢 ALERT" else ''), subset=['Signal'])\
              .map(lambda v: 'color: #dc3545' if v > 70 else ('color: #28a745' if v < 30 else ''), subset=['RSI']),
            column_order=["Signal", "Tier", "Ticker", "Price", "Diff S1", "RSI", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
            hide_index=True, use_container_width=True
        )

except Exception as e:
    st.error(f"An error occurred: {e}")
