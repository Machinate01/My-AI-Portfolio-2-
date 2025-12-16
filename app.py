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
        "RKLB", "ASTS", "EOSE", "IREN", "WBD", "CRWV", "KO", "PG", "WM", "UBER", "SCHD"
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

    # รวม Ticker ทั้งหมดเพื่อดึงข้อมูลทีเดียว
    port_tickers = [item['Ticker'] for item in my_portfolio_data]
    all_tickers = list(set(port_tickers + my_watchlist_tickers))

    # --- 3. ฟังก์ชันดึงราคาและคำนวณ Technical (Yahoo Finance Engine) ---
    @st.cache_data(ttl=30, show_spinner="Fetching Real-time Market Data...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        
        # Download data for all tickers (1 Year History for EMA200)
        try:
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=True)
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            return {}

        for ticker in tickers_list:
            try:
                if len(tickers_list) > 1:
                    df_t = df_hist[ticker].copy()
                else:
                    df_t = df_hist.copy()

                df_t = df_t.dropna()
                if df_t.empty: continue

                # 1. Price Data
                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                
                # 2. Calculate Indicators
                df_t['EMA50'] = df_t['Close'].ewm(span=50, adjust=False).mean()
                df_t['EMA200'] = df_t['Close'].ewm(span=200, adjust=False).mean()
                
                # RSI (14)
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_t['RSI'] = 100 - (100 / (1 + rs))

                # Dynamic Sell Levels (BB & High)
                df_t['SMA20'] = df_t['Close'].rolling(window=20).mean()
                df_t['STD20'] = df_t['Close'].rolling(window=20).std()
                sell_r1 = (df_t['SMA20'] + (df_t['STD20'] * 2)).iloc[-1]
                sell_r2 = df_t['Close'].iloc[-252:].max()

                ema50 = df_t['EMA50'].iloc[-1]
                ema200 = df_t['EMA200'].iloc[-1]
                rsi_val = df_t['RSI'].iloc[-1]

                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": ema50, "EMA200": ema200, "RSI": rsi_val,
                    "Sell1": sell_r1, "Sell2": sell_r2
                }
            except Exception as e:
                data_dict[ticker] = {
                    "Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0, "Sell2": 0
                }
                
        return data_dict

    if st.button('🔄 Refresh Data (Real-time)'):
        st.cache_data.clear()
        st.rerun()

    market_data = get_realtime_data(all_tickers)

    # --- 4. คำนวณพอร์ต (Processing) ---
    df = pd.DataFrame(my_portfolio_data)
    
    df['Current Price'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('Price', 0))
    df['PrevClose'] = df['Ticker'].apply(lambda x: market_data.get(x, {}).get('PrevClose', 0))
    
    df['Value USD'] = df['Qty'] * df['Current Price']
    df['Total Cost'] = df['Qty'] * df['Avg Cost']
    df['Total Gain USD'] = df['Value USD'] - df['Total Cost']
    df['%G/L'] = ((df['Current Price'] - df['Avg Cost']) / df['Avg Cost']) 
    df['Day Change USD'] = (df['Current Price'] - df['PrevClose']) * df['Qty']
    df['%Day Change'] = ((df['Current Price'] - df['PrevClose']) / df['PrevClose']) if df['PrevClose'].sum() > 0 else 0

    def get_levels_series(ticker, price):
        data = market_data.get(ticker, {})
        buy1 = data.get('EMA50', 0)
        buy2 = data.get('EMA200', 0)
        diff_s1 = (price - buy1) / buy1 if buy1 > 0 else 0
        return pd.Series([buy1, buy2, data.get('Sell1', 0), data.get('Sell2', 0), diff_s1], 
                         index=['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2', 'Diff S1'])

    tech_cols = df.apply(lambda x: get_levels_series(x['Ticker'], x['Current Price']), axis=1)
    df = pd.concat([df, tech_cols], axis=1)

    total_value = df['Value USD'].sum() + cash_balance_usd
    total_gain = df['Total Gain USD'].sum()
    total_day_change = df['Day Change USD'].sum()
    total_invested = df['Total Cost'].sum()

    # --- 5. แสดงผล (UI) ---
    st.title("🔭 My Portfolio & Watchlist") 
    st.caption(f"Last Update (BKK Time): {target_date_str} | Data Source: Yahoo Finance")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*33:,.0f}")
    c2.metric("🌊 Cash Pool", f"${cash_balance_usd:,.2f}", "Ready to Sniper")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Invested: ${total_invested:,.0f}")
    c4.metric("📅 Day Change", f"${total_day_change:+.2f}", f"{(total_day_change/total_invested*100):+.2f}%")

    st.markdown("---")

    col_mid_left, col_mid_right = st.columns([2, 1])
    with col_mid_left:
        with st.expander("🧠 Strategy: Nasdaq 24/5 & EMA Indicators", expanded=False):
            st.markdown("""
            * **📊 EMA Indicator Levels (Real-time):**
                * **Buy Lv.1 (EMA 50):** จุดเข้าซื้อตามเทรนด์ (Sniper Zone)
                * **Buy Lv.2 (EMA 200):** จุดรับของถูก (Deep Value / Floor)
                * **Sell Lv.1:** Upper Bollinger Band (แนวต้านระยะสั้น)
                * **Sell Lv.2:** 52-Week High (จุดสูงสุดเดิม)
            """)
        
        with st.expander("📅 Weekly Analysis: 16-18 Dec (Consumer, AI, Inflation)", expanded=True):
            st.markdown("""
            * **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**
                * **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ
            * **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**
                * **Event:** งบ **Micron (MU)** 🚨 *Highlight*
                * ถ้า "ดีมานด์ AI ล้น" → **NVDA & TSM** พุ่ง 🚀
            * **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
                * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน
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

    # --- Styling Functions (NEW LOGIC) ---
    def color_text(val):
        if isinstance(val, (int, float)): return 'color: #28a745' if val >= 0 else 'color: #dc3545'
        return ''
    
    # [UPDATED] Diff S1 Color Logic
    def color_diff_s1_logic(val):
        if isinstance(val, (int, float)):
            if val < 0: # ติดลบ (ของถูก) -> เขียวเข้ม
                return 'color: #28a745; font-weight: bold;' 
            elif 0 <= val <= 0.02: # บวกเล็กน้อย -> เขียวปกติ
                return 'color: #90EE90;' 
            else: # บวกเยอะ -> แดง
                return 'color: #dc3545;'
        return ''

    def color_rsi(val):
        if val >= 70: return 'color: #dc3545; font-weight: bold;' # Red (Overbought)
        if val <= 30: return 'color: #28a745; font-weight: bold;' # Green (Oversold)
        return ''

    def format_arrow(val):
        symbol = "⬆️" if val > 0 else "⬇️" if val < 0 else "➖"
        return f"{val:+.2%} {symbol}"

    # --- LEFT SIDE: Portfolio ---
    with col_bot_left:
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
            .map(color_diff_s1_logic, subset=['Diff S1']), # Apply New Logic
            column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "%G/L", "Current Price", "Value USD", "Total Gain USD", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
            column_config={
                "Current Price": "Price", "%G/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)"
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
            .map(color_diff_s1_logic, subset=['Diff S1']), # Apply New Logic
            column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "%G/L", "Current Price", "Value USD", "Total Gain USD", "Diff S1", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
            column_config={
                "Current Price": "Price", "%G/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)"
            },
            hide_index=True, use_container_width=True
        )

    # --- RIGHT SIDE: Watchlist ---
    with col_bot_right:
        st.subheader("🎯 Sniper Watchlist (Fractional Unlocked)")
        
        watchlist_data = []
        for t in sorted(list(set(my_watchlist_tickers))): 
            data = market_data.get(t, {})
            price = data.get('Price', 0)
            prev = data.get('PrevClose', 0)
            pct_change = (price - prev) / prev if prev > 0 else 0
            
            # Real-time Indicators
            buy1 = data.get('EMA50', 0)
            buy2 = data.get('EMA200', 0)
            sell1 = data.get('Sell1', 0)
            sell2 = data.get('Sell2', 0)
            rsi = data.get('RSI', 50)
            
            # Logic Calculation
            diff_s1 = (price - buy1)/buy1 if buy1 > 0 else 9.99
            
            signal = "4. Wait" 
            if price <= buy1 and price > 0: signal = "1. ✅ IN ZONE"
            elif diff_s1 <= 0.02 and price > 0: signal = "2. 🟢 ALERT"
            elif price >= sell1: signal = "5. 🔴 PROFIT"
            else: signal = "3. ➖ Wait"
            
            watchlist_data.append({
                "Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": price, "% Day": pct_change, "Signal": signal, 
                "Diff S1": diff_s1, "RSI": rsi,
                "Buy Lv.1": buy1, "Buy Lv.2": buy2, "Sell Lv.1": sell1, "Sell Lv.2": sell2,
                "Display Signal": signal.split(". ")[1] 
            })
        
        df_watch = pd.DataFrame(watchlist_data)
        df_watch = df_watch.sort_values(by=["Signal", "Diff S1"], ascending=[True, True])

        def highlight_row(s):
            if "IN ZONE" in s['Signal']: return ['background-color: rgba(40, 167, 69, 0.4)'] * len(s)
            elif "ALERT" in s['Signal']: return ['background-color: rgba(40, 167, 69, 0.2)'] * len(s)
            elif "PROFIT" in s['Signal']: return ['background-color: rgba(220, 53, 69, 0.2)'] * len(s)
            return [''] * len(s)

        st.dataframe(
            df_watch.style.format({
                "Price": "${:.2f}", "% Day": format_arrow, "Diff S1": "{:+.1%}", "RSI": "{:.0f}",
                "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
            })
            .apply(highlight_row, axis=1)
            .map(color_diff_s1_logic, subset=['Diff S1']) # Apply New Logic
            .map(color_tier, subset=['Tier'])
            .map(color_rsi, subset=['RSI']), 
            column_config={
                "Display Signal": st.column_config.Column("Status", width="medium"),
                "Tier": st.column_config.Column("Tier", width="small"),
                "Ticker": st.column_config.Column("Symbol", width="small"),
                "Price": st.column_config.Column("Price", width="small"),
                "% Day": st.column_config.Column("% Day", width="small"),
                "Diff S1": st.column_config.Column("Diff S1", help="Distance to EMA 50"),
                "RSI": st.column_config.Column("RSI", help="RSI (14)"),
                "Buy Lv.1": st.column_config.Column("Buy (EMA50)"),
                "Buy Lv.2": st.column_config.Column("Buy (EMA200)"),
                "Sell Lv.1": st.column_config.Column("Sell (R1)"),
                "Sell Lv.2": st.column_config.Column("Sell (R2)"),
            },
            column_order=["Display Signal", "Tier", "Ticker", "Price", "% Day", "Diff S1", "RSI", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
            hide_index=True, use_container_width=True
        )

except Exception as e:
    st.error(f"System Error: {e}")
