# --- ส่วนแก้บั๊ก Cache และ Imports ---
import appdirs as ad
ad.user_cache_dir = lambda *args: "/tmp"

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="My Portfolio & Watchlist", page_icon="🔭", layout="wide")

# CSS ปรับแต่ง
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'sans-serif'; }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800; }
    div[data-testid="stDataFrame"] p { font-size: 1.1rem !important; font-family: 'Courier New', monospace; }
    h3 { padding-top: 0.5rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 1.5rem !important; }
    .stAlert { margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ปุ่ม Refresh
if st.button('🔄 Refresh Data (Real-time)'):
    st.rerun()

# --- 2. ข้อมูลพอร์ต ---
start_date_str = "02/10/2025" 
cash_balance_usd = 90.00 

now = datetime.utcnow() + timedelta(hours=7) 
target_date_str = now.strftime("%d %B %Y %H:%M:%S")

try:
    start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
    invest_days = (now - datetime.combine(start_date, datetime.min.time()) - timedelta(hours=7)).days
except:
    invest_days = 0

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
    "NFLX": "A", "WM": "A", "WMT": "A", "CEG": "A", "NET": "A", "PANW": "A",
    "ISRG": "B+", "RKLB": "B+", "TMDX": "B+", "IREN": "B+", "MELI": "B+", "ASTS": "B+", "EOSE": "B+", "SCHD": "B+",
    "ADBE": "B", "UBER": "B", "HOOD": "B", "DASH": "B", "BABA": "B", "CRWV": "B", "MU": "B", "PATH": "C",
    "TTD": "C", "LULU": "C", "CMG": "C", "DUOL": "C", "PDD": "C", "ORCL": "C", "WBD": "Hold",
    "VOO": "ETF", "QQQM": "ETF"
}

# 2.3 แนวรับ-แนวต้านทางเทคนิค
tech_levels = {
    "AMZN": [250, 235, 216, 195], 
    "AAPL": [300, 285, 260, 240], 
    "GOOGL": [340, 320, 290, 270], 
    "NVDA": [210, 190, 165, 145], 
    "META": [720, 680, 630, 580], 
    "MSFT": [520, 490, 460, 430], 
    "TSLA": [550, 500, 400, 350], 
    "PLTR": [220, 200, 175, 150],
    "AMD": [250, 230, 200, 180], 
    "AVGO": [380, 360, 330, 300],
    "TSM": [320, 300, 270, 250], 
    "LLY": [1200, 1150, 1000, 950],
    "V": [380, 365, 340, 320], 
    "VOO": [660, 640, 615, 590],
    "IREN": [70, 55, 38, 25],
    "RKLB": [75, 65, 50, 40],
    "UBER": [110, 95, 82, 70],
    "CDNS": [350, 330, 290, 270],
    "WM": [245, 230, 215, 205],
    "ASTS": [80, 70, 55, 45],
    "EOSE": [20, 16, 12, 9],
    "KO": [80, 75, 68, 64],
    "PG": [165, 155, 142, 135],
    "CRWV": [80, 70, 55, 45],
    "SCHD": [32, 30, 28, 26],
    "SMH": [380, 360, 340, 320],
    "QQQ": [640, 620, 590, 560]
}

# --- 3. ฟังก์ชันดึงราคา ---
@st.cache_data(ttl=60, show_spinner="Fetching Market Data...") 
def get_all_data(portfolio_data, watchlist_tickers):
    port_tickers = [item['Ticker'] for item in portfolio_data]
    all_tickers = list(set(port_tickers + watchlist_tickers))
    
    simulated_prices = {
        "AMZN": 222.54, "V": 346.89, "LLY": 1062.19, "NVDA": 176.29, "VOO": 625.96, "TSM": 287.14,
        "PLTR": 183.25, "TSLA": 475.31, "RKLB": 55.41, "GOOGL": 308.22, "META": 647.51, "MSFT": 474.82,
        "AMD": 207.58, "AVGO": 339.81, "IREN": 40.13, "ASTS": 67.81, "EOSE": 13.63, "PATH": 16.16, "WBD": 29.71,
        "CRWV": 58.50, "SCHD": 28.50, "SMH": 352.90, "QQQ": 610.54
    }

    try:
        usd_thb_data = yf.Ticker("THB=X").history(period="1d")
        usd_thb = usd_thb_data['Close'].iloc[-1] if not usd_thb_data.empty else 31.47
    except:
        usd_thb = 31.47
        
    live_prices = {}
    prev_closes = {}
    
    for t in all_tickers:
        if t in simulated_prices:
            live_prices[t] = simulated_prices[t]
            if t == "TSLA": prev_closes[t] = simulated_prices[t] / 1.0356
            elif t == "LLY": prev_closes[t] = simulated_prices[t] / 1.1044
            elif t == "RKLB": prev_closes[t] = simulated_prices[t] / 0.9011
            else: prev_closes[t] = simulated_prices[t] 
        else:
            try:
                hist = yf.Ticker(t).history(period="5d")
                if not hist.empty:
                    live_prices[t] = hist['Close'].iloc[-1]
                    if len(hist) >= 2:
                        prev_closes[t] = hist['Close'].iloc[-2]
                    else:
                        prev_closes[t] = live_prices[t]
                else:
                    live_prices[t] = 0
                    prev_closes[t] = 0
            except:
                live_prices[t] = 0
                prev_closes[t] = 0
            
    return live_prices, prev_closes, usd_thb

# --- 4. ประมวลผล ---
fetched_prices, prev_closes, exchange_rate = get_all_data(my_portfolio_data, my_watchlist_tickers)

df = pd.DataFrame(my_portfolio_data)
df['Current Price'] = df['Ticker'].map(fetched_prices)
df['Prev Close'] = df['Ticker'].map(prev_closes)
df['Value USD'] = df['Qty'] * df['Current Price']
df['Total Cost'] = df['Qty'] * df['Avg Cost'] 
df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
df['%G/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
df['Day Change USD'] = (df['Current Price'] - df['Prev Close']) * df['Qty']
df['%Day Change'] = ((df['Current Price'] - df['Prev Close']) / df['Prev Close'])

def calculate_diff_s1(row):
    ticker = row['Ticker']
    price = row['Current Price']
    levels = tech_levels.get(ticker, [0, 0, 0, 0])
    s1 = levels[2]
    if s1 > 0:
        return (price - s1) / s1
    return 0

def get_levels(row):
    levels = tech_levels.get(row['Ticker'], [0, 0, 0, 0])
    return pd.Series([levels[2], levels[3], levels[1], levels[0]])

df['Diff S1'] = df.apply(calculate_diff_s1, axis=1)
df[['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2']] = df.apply(get_levels, axis=1)

total_invested_usd = df['Value USD'].sum()
total_equity_usd = total_invested_usd + cash_balance_usd 
total_equity_thb = total_equity_usd * exchange_rate
total_gain_usd = df['Total Gain USD'].sum()
total_day_change_usd = df['Day Change USD'].sum()

# --- 5. แสดงผล (UI) ---
st.title("🔭 My Portfolio & Watchlist") 
st.caption(f"Last Update (BKK Time): {target_date_str}")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("💰 Total Value (USD)", f"${total_equity_usd:,.2f}", f"≈฿{total_equity_thb:,.0f}")
col_m2.metric("🌊 Cash Pool", f"${cash_balance_usd:,.2f}", "Ready to Sniper")
col_m3.metric("📈 Unrealized G/L", f"${total_gain_usd:,.2f}", f"Invested: ${total_invested_usd:,.0f}")
col_m4.metric("📅 Day Change", f"${total_day_change_usd:+.2f}", f"{(total_day_change_usd/total_invested_usd*100):+.2f}%")

st.markdown("---")

col_mid_left, col_mid_right = st.columns([2, 1])
with col_mid_left:
    # --- Strategy Section 1 (เดิม) ---
    with st.expander("🧠 Strategy: Nasdaq 24/5 & EMA Indicators", expanded=False):
        st.markdown("""
        * **📊 EMA Indicator Levels:**
            * **Buy Lv.1 (EMA 50):** จุดเข้าซื้อตามเทรนด์ (Sniper Zone)
            * **Buy Lv.2 (EMA 200):** จุดรับของถูก (Deep Value / Floor)
            * **Sell Lv.1/Lv.2:** แนวต้านทำกำไรระยะสั้นและยาว
        * **🎯 New Watchlist:** เพิ่ม **SCHD** (Dividend Growth) เพื่อกระจายความเสี่ยง
        * **🌊 Action:** ใช้เงินสด $90 รอช้อนที่ **Buy Lv.1** ถ้าหลุดให้รอ **Buy Lv.2**
        """)
    
    # --- Strategy Section 2 (ใหม่) ---
    with st.expander("📅 Weekly Analysis: 16-18 Dec (Consumer, AI, Inflation)", expanded=True):
        st.markdown("""
        * **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**
            * **Events:** ยอดค้าปลีก (Retail Sales) & การจ้างงาน (Nonfarm Payrolls)
            * **Impact:**
                * **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ (คนซื้อของ/รูดบัตรน้อยลง)
                * **WBD:** ถ้าแรงงานแกร่ง = ดอกเบี้ยไม่ลง = ลบต่อหุ้นหนี้เยอะ
        * **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**
            * **Event:** งบ **Micron (MU)** 🚨 *Highlight*
            * **Impact:** MU ผลิตชิป HBM คู่กับ GPU
                * ถ้า "ดีมานด์ AI ล้น" → **NVDA & TSM** พุ่ง 🚀
                * ถ้า "สต็อกล้น/ชะลอ" → **NVDA & TSM** โดนเทขาย (Profit Taking) 📉
        * **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
            * **Events:** CPI, Accenture (ACN), FedEx (FDX)
            * **Impact:**
                * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน
                * **ACN:** ตัวชี้วัด AI Adoption (Phase 3) → ถ้าดี ส่งผลบวกกลุ่ม Software
                * **FDX:** ตัวชี้วัดเศรษฐกิจโลก → ถ้าลดเป้า **AMZN** หนาว
        """)

with col_mid_right:
    labels = list(df['Ticker']) + ['CASH 💵']
    values = list(df['Value USD']) + [cash_balance_usd]
    colors = ['#333333', '#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
    fig_pie = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.5, marker_colors=colors, textinfo='label+percent', textfont_size=14
    )])
    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250, showlegend=True,
        legend=dict(font=dict(size=10), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

col_bot_left, col_bot_right = st.columns(2) 

with col_bot_left:
    def color_text(val):
        if isinstance(val, (int, float)):
            return 'color: #28a745' if val >= 0 else 'color: #dc3545'
        return ''
    def format_arrow(val):
        symbol = "⬆️" if val > 0 else "⬇️" if val < 0 else "➖"
        return f"{val:+.2%} {symbol}"
    def color_diff_s1_main(val):
        if val <= 0.02: return 'color: #28a745; font-weight: bold;'
        return ''

    df_display = df.copy() 
    
    st.subheader("🚀 Growth Engine") 
    growth_tickers = ["NVDA", "TSM", "AMZN"]
    df_growth = df_display[df_display['Ticker'].isin(growth_tickers)].copy()
    
    st.dataframe(
        df_growth.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
            "Diff S1": "{:+.1%}", "%G/L": format_arrow, "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
            "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
        })
        .map(color_text, subset=['%G/L', 'Total Gain USD'])
        .map(color_diff_s1_main, subset=['Diff S1']),
        column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "%G/L", "Current Price", "Value USD", "Total Gain USD", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
        column_config={
            "Current Price": "Price",
            "%G/L": "% Total",
            "Value USD": "Value ($)",
            "Total Gain USD": "Total Gain ($)"
        },
        hide_index=True, use_container_width=True
    )

    st.subheader("🛡️ Defensive Wall") 
    defensive_tickers = ["V", "LLY", "VOO"]
    df_defensive = df[df['Ticker'].isin(defensive_tickers)].copy()
    
    st.dataframe(
        df_defensive.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
            "Diff S1": "{:+.1%}", "%G/L": format_arrow, "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
            "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
        })
        .map(color_text, subset=['%G/L', 'Total Gain USD'])
        .map(color_diff_s1_main, subset=['Diff S1']),
        column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "%G/L", "Current Price", "Value USD", "Total Gain USD", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
        column_config={
            "Current Price": "Price",
            "%G/L": "% Total",
            "Value USD": "Value ($)",
            "Total Gain USD": "Total Gain ($)"
        },
        hide_index=True, use_container_width=True
    )

with col_bot_right:
    st.subheader("🎯 Sniper Watchlist (Fractional Unlocked)")
    watchlist_data = []
    for t in sorted(list(set(my_watchlist_tickers))): 
        price = fetched_prices.get(t, 0)
        prev = prev_closes.get(t, 0)
        pct_change = (price - prev) / prev if prev > 0 else 0
        
        levels = tech_levels.get(t, [0, 0, 0, 0]) 
        s1 = levels[2] 
        signal = "4. Wait" 
        dist_to_s1 = 999.9
        if s1 > 0:
            dist_to_s1 = (price - s1) / s1 * 100 
            if price <= s1: signal = "1. ✅ IN ZONE"
            elif 0 < dist_to_s1 <= 2.0: signal = "2. 🟢 ALERT"
            elif price >= levels[1]: signal = "5. 🔴 PROFIT"
            else: signal = "3. ➖ Wait"
        
        watchlist_data.append({
            "Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": price, "% Day": pct_change, "Signal": signal, 
            "Diff S1": dist_to_s1/100, "Buy Lv.1": levels[2], "Buy Lv.2": levels[3], "Sell Lv.1": levels[1], "Sell Lv.2": levels[0],
            "Display Signal": signal.split(". ")[1] 
        })
    
    df_watch = pd.DataFrame(watchlist_data)
    df_watch = df_watch.sort_values(by=["Signal", "Diff S1"], ascending=[True, True])

    def highlight_row(s):
        if "IN ZONE" in s['Signal']: return ['background-color: rgba(40, 167, 69, 0.4)'] * len(s)
        elif "ALERT" in s['Signal']: return ['background-color: rgba(40, 167, 69, 0.2)'] * len(s)
        elif "PROFIT" in s['Signal']: return ['background-color: rgba(220, 53, 69, 0.2)'] * len(s)
        return [''] * len(s)
    def color_dist_s1(val):
        if val < 0: return 'color: #dc3545; font-weight: bold;'
        elif 0 <= val <= 0.02: return 'color: #28a745; font-weight: bold;'
        return ''
    def color_tier(val):
        if val == "S+": return 'color: #ffd700; font-weight: bold;' 
        if val == "S": return 'color: #c0c0c0; font-weight: bold;' 
        if "A" in val: return 'color: #cd7f32; font-weight: bold;' 
        return ''

    st.dataframe(
        df_watch.style.format({
            "Price": "${:.2f}", "% Day": format_arrow, "Diff S1": "{:+.1%}",
            "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
        }).apply(highlight_row, axis=1).map(color_dist_s1, subset=['Diff S1']).map(color_tier, subset=['Tier']),
        column_config={
            "Display Signal": st.column_config.Column("Status", width="medium"),
            "Tier": st.column_config.Column("Tier", width="small"),
            "Ticker": st.column_config.Column("Symbol", width="small"),
            "Price": st.column_config.Column("Price", width="small"),
            "% Day": st.column_config.Column("% Day", width="small"),
            "Diff S1": st.column_config.Column("Diff S1", help="Distance to EMA 50"),
            "Buy Lv.1": st.column_config.Column("Buy (EMA50)"),
            "Buy Lv.2": st.column_config.Column("Buy (EMA200)"),
            "Sell Lv.1": st.column_config.Column("Sell (R1)"),
            "Sell Lv.2": st.column_config.Column("Sell (R2)"),
        },
        column_order=["Display Signal", "Tier", "Ticker", "Price", "% Day", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
        hide_index=True, use_container_width=True
    )
