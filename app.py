import streamlit as st
import pandas as pd
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
</style>
""", unsafe_allow_html=True)

# --- 2. ข้อมูลพอร์ต (Mock Data) ---
try:
    start_date_str = "02/10/2025" 
    cash_balance_usd = 90.00 
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    # 2.1 พอร์ตหลัก
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
        "RKLB", "ASTS", 
        "EOSE", "IREN", "WBD", "CRWV",
        "KO", "PG", "WM", "UBER", "SCHD"
    ] 

    # PRB Tier Mapping
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

    # 2.3 แนวรับ-แนวต้าน (Updated for Dec 2025 Simulation)
    # Buy1=EMA50, Buy2=EMA200, Sell1=Res, Sell2=High
    tech_levels = {
        "AMZN": [250, 235, 216, 195], "AAPL": [300, 285, 260, 240], "GOOGL": [340, 320, 290, 270], 
        "NVDA": [210, 190, 165, 145], "META": [720, 680, 630, 580], "MSFT": [520, 490, 460, 430], 
        "TSLA": [550, 500, 400, 350], "PLTR": [220, 200, 175, 150], "AMD": [250, 230, 200, 180], 
        "AVGO": [380, 360, 330, 300], "TSM": [320, 300, 270, 250], "LLY": [1200, 1150, 1000, 950],
        "V": [380, 365, 340, 320], "VOO": [660, 640, 615, 590], "IREN": [70, 55, 38, 25],
        "RKLB": [75, 65, 50, 40], "UBER": [110, 95, 82, 70], "CDNS": [350, 330, 290, 270],
        "WM": [245, 230, 215, 205], "ASTS": [80, 70, 55, 45], "EOSE": [20, 16, 12, 9],
        "KO": [80, 75, 68, 64], "PG": [165, 155, 142, 135], "CRWV": [80, 70, 55, 45],
        "SCHD": [32, 30, 28, 26], "SMH": [380, 360, 340, 320], "QQQ": [640, 620, 590, 560],
        # [NEW] Updated Watchlist Levels (Simulated for 2025)
        "CRWD": [540, 515, 480, 450], "MU": [265, 250, 220, 160], "PATH": [24, 20, 14.5, 13],
        "QQQM": [270, 260, 250, 240], "WBD": [50, 34, 20, 15]
    }

    # --- 3. ฟังก์ชันดึงราคา (Simulated Mode) ---
    @st.cache_data(ttl=60, show_spinner=False)
    def get_market_data():
        # ราคาสมมติให้ตรงกับภาพที่คุณส่งมา (Dec 2025)
        prices = {
            "AMZN": 222.54, "V": 346.89, "LLY": 1062.19, "NVDA": 176.29, "VOO": 625.96, "TSM": 287.14,
            "PLTR": 183.25, "TSLA": 475.31, "RKLB": 55.41, "GOOGL": 308.22, "META": 647.51, "MSFT": 474.82,
            "AMD": 207.58, "AVGO": 339.81, "IREN": 40.13, "ASTS": 67.81, "EOSE": 13.63, "PATH": 16.16, "WBD": 29.71,
            "CRWV": 58.50, "SCHD": 28.50, "SMH": 352.90, "QQQ": 610.54, "QQQM": 251.36, "CRWD": 487.47, "MU": 237.50,
            "AAPL": 274.11, "PG": 145.13, "KO": 70.97, "WM": 218.32, "UBER": 81.86
        }
        return prices

    prices = get_market_data()

    # --- 4. คำนวณพอร์ต ---
    df = pd.DataFrame(my_portfolio_data)
    df['Current Price'] = df['Ticker'].map(prices)
    df['Value USD'] = df['Qty'] * df['Current Price']
    df['Total Cost'] = df['Qty'] * df['Avg Cost']
    df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
    df['%G/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
    
    # Calculate Levels
    def get_levels(ticker):
        lv = tech_levels.get(ticker, [0,0,0,0])
        return pd.Series([lv[2], lv[3], lv[1], lv[0]], index=['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2'])

    level_cols = df['Ticker'].apply(get_levels)
    df = pd.concat([df, level_cols], axis=1)

    # Calculate Diff S1
    df['Diff S1'] = df.apply(lambda x: (x['Current Price'] - x['Buy Lv.1'])/x['Buy Lv.1'] if x['Buy Lv.1']>0 else 0, axis=1)

    total_value = df['Value USD'].sum() + cash_balance_usd
    total_gain = df['Total Gain USD'].sum()

    # --- 5. แสดงผล (UI) ---
    st.title("🔭 My Portfolio & Watchlist") 
    st.caption(f"Last Update (BKK Time): {target_date_str}")

    # Scorecard
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value", f"${total_value:,.2f}")
    c2.metric("🌊 Cash Pool", f"${cash_balance_usd:,.2f}", "Ready")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}")
    c4.metric("📅 Market Status", "OPEN", "Nasdaq 24/5")

    st.markdown("---")

    # Strategy Section
    c_mid_L, c_mid_R = st.columns([2, 1])
    with c_mid_L:
        with st.expander("🧠 Strategy: Nasdaq 24/5 & EMA Indicators", expanded=True):
            st.markdown("""
            * **📊 EMA Indicator Levels:**
                * **Buy Lv.1 (EMA 50):** จุดเข้าซื้อตามเทรนด์ (Sniper Zone)
                * **Buy Lv.2 (EMA 200):** จุดรับของถูก (Deep Value / Floor)
            * **🎯 New Watchlist:** เพิ่ม **SCHD** (Dividend Growth) เพื่อกระจายความเสี่ยง
            * **🌊 Action:** ใช้เงินสด $90 รอช้อนที่ **Buy Lv.1** ถ้าหลุดให้รอ **Buy Lv.2**
            """)
    with c_mid_R:
        # Pie Chart
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
        # Styling Functions
        def style_df(dframe):
            return dframe.style.format({
                "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}", "Diff S1": "{:+.1%}", "%G/L": "{:+.2%}",
                "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
            }).map(lambda v: 'color: #28a745' if v > 0 else 'color: #dc3545', subset=['Total Gain USD', '%G/L'])\
              .map(lambda v: 'color: #28a745; font-weight: bold' if v <= 0.02 else '', subset=['Diff S1'])

        # Growth
        st.subheader("🚀 Growth Engine")
        growth_tickers = ["NVDA", "TSM", "AMZN"]
        df_growth = df[df['Ticker'].isin(growth_tickers)].copy()
        st.dataframe(
            style_df(df_growth),
            column_order=["Ticker", "Qty", "Avg Cost", "Total Cost", "Current Price", "Value USD", "Diff S1", "Buy Lv.1", "Buy Lv.2"],
            hide_index=True, use_container_width=True
        )

        # Defensive
        st.subheader("🛡️ Defensive Wall")
        def_tickers = ["V", "LLY", "VOO"]
        df_def = df[df['Ticker'].isin(def_tickers)].copy()
        st.dataframe(
            style_df(df_def),
            column_order=["Ticker", "Qty", "Avg Cost", "Total Cost", "Current Price", "Value USD", "Diff S1", "Buy Lv.1", "Buy Lv.2"],
            hide_index=True, use_container_width=True
        )

    # --- RIGHT: Watchlist ---
    with col_right:
        st.subheader("🎯 Sniper Watchlist")
        
        watch_data = []
        for t in sorted(list(set(my_watchlist_tickers))):
            price = prices.get(t, 0)
            lv = tech_levels.get(t, [0,0,0,0]) # Sell2, Sell1, Buy1, Buy2
            
            # Signal Logic
            diff_s1 = (price - lv[2])/lv[2] if lv[2] > 0 else 9.99
            signal = "Wait"
            if price <= lv[2]: signal = "✅ BUY"
            elif diff_s1 <= 0.02: signal = "🟢 ALERT"
            
            watch_data.append({
                "Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": price, 
                "Signal": signal, "Diff S1": diff_s1,
                "Buy Lv.1": lv[2], "Buy Lv.2": lv[3], "Sell Lv.1": lv[1], "Sell Lv.2": lv[0]
            })
            
        df_watch = pd.DataFrame(watch_data).sort_values("Diff S1")
        
        st.dataframe(
            df_watch.style.format({
                "Price": "${:.2f}", "Diff S1": "{:+.1%}", 
                "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
            }).map(lambda v: 'background-color: #28a74544' if v == "✅ BUY" else ('background-color: #28a74522' if v == "🟢 ALERT" else ''), subset=['Signal']),
            column_order=["Signal", "Tier", "Ticker", "Price", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
            hide_index=True, use_container_width=True
        )

except Exception as e:
    st.error(f"An error occurred: {e}")
