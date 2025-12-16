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
    div[data-testid="stDataFrame"] p { font-size: 1.15rem !important; font-family: 'Courier New', monospace; }
    h3 { padding-top: 0.5rem; border-bottom: 3px solid #444; padding-bottom: 0.5rem; font-size: 1.5rem !important; }
    .stAlert { margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ปุ่ม Refresh
if st.button('🔄 Refresh Data (Real-time)'):
    st.rerun()

# --- 2. ข้อมูลพอร์ต (Updated: 16 Dec 2025) ---
start_date_str = "02/10/2025" 
cash_balance_usd = 90.00 

# เวลาไทย
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
    "KO", "PG", "WM", "UBER" 
] 

# PRB Tier Mapping
prb_tiers = {
    "NVDA": "S+", "AAPL": "S+", "MSFT": "S+", "GOOGL": "S+", "TSM": "S+", "ASML": "S+",
    "AMD": "S", "PLTR": "S", "AMZN": "S", "META": "S", "AVGO": "S", "CRWD": "S", "SMH": "S", "QQQ": "ETF",
    "TSLA": "A+", "V": "A+", "MA": "A+", "LLY": "A+", "JNJ": "A+", "BRK.B": "A+", "PG": "B+", "KO": "B+",
    "NFLX": "A", "WM": "A", "WMT": "A", "CEG": "A", "NET": "A", "PANW": "A",
    "ISRG": "B+", "RKLB": "B+", "TMDX": "B+", "IREN": "B+", "MELI": "B+", "ASTS": "B+", "EOSE": "B+",
    "ADBE": "B", "UBER": "B", "HOOD": "B", "DASH": "B", "BABA": "B", "CRWV": "B", "MU": "B", "PATH": "C",
    "TTD": "C", "LULU": "C", "CMG": "C", "DUOL": "C", "PDD": "C", "ORCL": "C", "WBD": "Hold",
    "VOO": "ETF", "QQQM": "ETF"
}

# 2.3 แนวรับ-แนวต้านทางเทคนิค
tech_levels = {
    "AMZN": [230, 244, 216, 212], 
    "AAPL": [280, 288, 268, 260], 
    "GOOGL": [320, 330, 300, 288], 
    "NVDA": [182, 196, 173, 167], 
    "META": [675, 700, 640, 632], 
    "MSFT": [490, 505, 468, 457], 
    "TSLA": [480, 500, 460, 445], 
    "PLTR": [195, 205, 180, 175],
    "AMD": [224, 238, 205, 199], 
    "AVGO": [350, 370, 335, 316],
    "TSM": [300, 310, 275, 268], 
    "LLY": [1100, 1150, 1000, 980],
    "V": [355, 365, 340, 330], 
    "VOO": [635, 650, 615, 600],
    "IREN": [50, 60, 38, 35],
    "RKLB": [60, 65, 50, 45],
    "UBER": [95, 100, 82, 78],
    "CDNS": [320, 330, 290, 280],
    "WM": [230, 235, 215, 210],
    "ASTS": [70, 75, 60, 55],
    "EOSE": [15, 18, 12, 10],
    "KO": [72, 75, 68, 65],
    "PG": [150, 155, 140, 138],
    "CRWV": [65, 70, 55, 50]
}

# --- 3. ฟังก์ชันดึงราคา ---
@st.cache_data(ttl=60, show_spinner="Fetching Market Data...") 
def get_all_data(portfolio_data, watchlist_tickers):
    port_tickers = [item['Ticker'] for item in portfolio_data]
    all_tickers = list(set(port_tickers + watchlist_tickers))
    
    # Mock Data
    simulated_prices = {
        "AMZN": 222.54, "V": 346.89, "LLY": 1062.19, "NVDA": 176.29, "VOO": 625.96, "TSM": 287.14,
        "PLTR": 183.25, "TSLA": 475.31, "RKLB": 55.41, "GOOGL": 308.22, "META": 647.51, "MSFT": 474.82,
        "AMD": 207.58, "AVGO": 339.81, "IREN": 40.13, "ASTS": 67.81, "EOSE": 13.63, "PATH": 16.16, "WBD": 29.71,
        "CRWV": 58.50 
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
df['Cost USD'] = df['Qty'] * df['Avg Cost']
df['Total Gain USD'] = df['Value USD'] - df['Cost USD']
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
    
df['Diff S1'] = df.apply(calculate_diff_s1, axis=1)

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

# --- Layout: แถวกลาง (บทความ + กราฟ) ---
col_mid_left, col_mid_right = st.columns([2, 1])

with col_mid_left:
    with st.expander("🧠 Strategy: Nasdaq 24/5 & The Asian Advantage", expanded=True):
        st.markdown("""
        * **🌍 Global 24/5 (Start Late 2026):** Nasdaq เตรียมเปิดเทรด 24 ชม.
        * **🇹🇭 Asian Sniper Advantage:**
            * ช่วง Night Session (21:00-04:00 US) ตรงกับ **09:00-16:00 ไทย**
            * **Benefit:** คุณจะเทรด NVDA, AMZN, TSLA ได้ในเวลางาน ไม่ต้องอดนอน!
            * **Warning:** สภาพคล่องต่ำ = ผันผวนสูง -> **Must use Limit Order Only!**
        * **🌊 Current Action:** ถือเงินสด $90 รอ Sniper หุ้น Growth ที่ย่อตัวในจังหวะเผลอ
        """)

with col_mid_right:
    labels = list(df['Ticker']) + ['CASH 💵']
    values = list(df['Value USD']) + [cash_balance_usd]
    colors = ['#333333', '#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.5,
        marker_colors=colors, textinfo='label+percent',
        textfont_size=14
    )])
    fig_pie.update_layout(
        margin=dict(t=10, b=10, l=10, r=10), 
        height=250, 
        showlegend=True,
        legend=dict(font=dict(size=10), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --- Layout: แถวล่าง (พอร์ตซ้าย + Watchlist ขวา) ---
col_bot_left, col_bot_right = st.columns([1.3, 2.7]) 

# --- ส่วนซ้าย: Main Portfolio ---
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

    df_display = df[['Ticker', 'Qty', 'Avg Cost', 'Current Price', 'Diff S1', '%Day Change', '%G/L', 'Value USD']].copy()
    df_display.columns = ['Ticker', 'Qty', 'Avg Cost', 'Price', 'Diff S1', '% Day', '% Total', 'Value ($)']
    
    st.subheader("🚀 Growth Engine") 
    growth_tickers = ["NVDA", "TSM", "AMZN"]
    df_growth = df_display[df_display['Ticker'].isin(growth_tickers)]
    
    st.dataframe(
        df_growth.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Price": "${:.2f}",
            "Diff S1": "{:+.1%}", "% Day": format_arrow, "% Total": format_arrow, "Value ($)": "${:,.2f}"
        })
        .map(color_text, subset=['% Day', '% Total'])
        .map(color_diff_s1_main, subset=['Diff S1']),
        hide_index=True, use_container_width=True
    )

    st.subheader("🛡️ Defensive Wall") 
    defensive_tickers = ["V", "LLY", "VOO"]
    df_defensive = df_display[df_display['Ticker'].isin(defensive_tickers)]
    
    st.dataframe(
        df_defensive.style.format({
            "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Price": "${:.2f}",
            "Diff S1": "{:+.1%}", "% Day": format_arrow, "% Total": format_arrow, "Value ($)": "${:,.2f}"
        })
        .map(color_text, subset=['% Day', '% Total'])
        .map(color_diff_s1_main, subset=['Diff S1']),
        hide_index=True, use_container_width=True
    )

# --- ส่วนขวา: Watchlist ---
with col_bot_right:
    st.subheader("🎯 Sniper Watchlist (Fractional Unlocked)")
    
    watchlist_data = []
    for t in sorted(list(set(my_watchlist_tickers))): 
        price = fetched_prices.get(t, 0)
        prev = prev_closes.get(t, 0)
        change = price - prev
        pct_change = (change / prev) if prev > 0 else 0
        
        levels = tech_levels.get(t, [0, 0, 0, 0]) 
        s1 = levels[2]
        r1 = levels[0]
        
        # Sniper Logic
        signal = "4. Wait" 
        dist_to_s1 = 999.9
        
        if s1 > 0:
            dist_to_s1 = (price - s1) / s1 * 100 
            
            if price <= s1:
                signal = "1. ✅ IN ZONE"
            elif 0 < dist_to_s1 <= 2.0:
                signal = "2. 🟢 ALERT"
            elif price >= r1:
                signal = "5. 🔴 PROFIT"
            else:
                signal = "3. ➖ Wait"
        
        watchlist_data.append({
            "Tier": prb_tiers.get(t, "-"),
            "Ticker": t,
            "Price": price,
            "% Day": pct_change,
            "Signal": signal, 
            "Dist S1": dist_to_s1/100,
            "รับ 1": levels[2],
            "ต้าน 1": levels[0],
            "Display Signal": signal.split(". ")[1] 
        })
    
    df_watch = pd.DataFrame(watchlist_data)
    df_watch = df_watch.sort_values(by=["Signal", "Dist S1"], ascending=[True, True])

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
        df_watch.style
        .format({
            "Price": "${:.2f}",
            "% Day": format_arrow,
            "Dist S1": "{:+.1%}",
            "รับ 1": "${:.0f}",
            "ต้าน 1": "${:.0f}"
        })
        .apply(highlight_row, axis=1)
        .map(color_dist_s1, subset=['Dist S1'])
        .map(color_tier, subset=['Tier']),
        column_config={
            "Display Signal": st.column_config.Column("Status", width="medium"),
            "Tier": st.column_config.Column("Tier", width="small"),
            "Ticker": st.column_config.Column("Symbol", width="small"),
            "Price": st.column_config.Column("Price", width="small"),
            "% Day": st.column_config.Column("% Day", width="small"),
            "Signal": None,
            "Dist S1": st.column_config.Column("Diff S1", help="ระยะห่างจากแนวรับไม้แรก"),
            "รับ 1": st.column_config.Column("Buy Lv.1"),
            "ต้าน 1": st.column_config.Column("Sell Lv.1"),
        },
        column_order=["Display Signal", "Tier", "Ticker", "Price", "% Day", "Dist S1", "รับ 1", "ต้าน 1"],
        hide_index=True, use_container_width=True
    )
