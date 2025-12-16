import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="My Portfolio & Watchlist", page_icon="🔭", layout="wide")

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

# --- 2. Initialize Session State (ระบบความจำ & ข้อมูลเริ่มต้น) ---

# 2.1 Portfolio Data
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "AMZN", "Category": "Growth", "Avg Cost": 228.0932, "Qty": 0.4157950},
        {"Ticker": "NVDA", "Category": "Growth", "Avg Cost": 178.7260, "Qty": 0.3351499},
        {"Ticker": "TSM",  "Category": "Growth", "Avg Cost": 274.9960, "Qty": 0.1118198},
        {"Ticker": "V",    "Category": "Defensive", "Avg Cost": 330.2129, "Qty": 0.2419045},
        {"Ticker": "LLY",  "Category": "Defensive", "Avg Cost": 961.8167, "Qty": 0.0707723},
        {"Ticker": "VOO",  "Category": "Defensive", "Avg Cost": 628.1220, "Qty": 0.0614849},
    ]

# 2.2 Watchlist Data
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        "AAPL", "PLTR", "GOOGL", "META", "MSFT", "TSLA", "AMD", "AVGO", "SMH", "QQQ", "QQQM", "MU", "CRWD", "PATH",
        "RKLB", "ASTS", "EOSE", "IREN", "WBD", "CRWV", "KO", "PG", "WM", "UBER", "SCHD"
    ]

# 2.3 Weekly Note Data (บทความวิเคราะห์)
if 'weekly_note' not in st.session_state:
    st.session_state.weekly_note = """* **วันอังคาร 16 ธ.ค.: "วัดชีพจรผู้บริโภค"**
    * **AMZN & V:** ถ้า Retail ต่ำกว่า +0.3% หรือ Nonfarm แย่ = ลบ
* **วันพุธ 17 ธ.ค.: "ชี้ชะตา AI (ภาค Hardware)"**
    * **Event:** งบ **Micron (MU)** 🚨 *Highlight*
    * ถ้า "ดีมานด์ AI ล้น" → **NVDA & TSM** พุ่ง 🚀
* **วันพฤหัส 18 ธ.ค.: "เงินเฟ้อ & AI (ภาคใช้งาน)"**
    * **CPI > 3.1%:** เงินเฟ้อมา → Tech (NVDA/AMZN) ร่วงก่อน"""

# --- 3. Sidebar Settings & Management ---
with st.sidebar:
    st.header("💼 Wallet & Management")
    cash_balance_usd = st.number_input("Cash Flow ($)", value=90.00, step=10.0, format="%.2f")
    
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
                    st.session_state.portfolio.append({
                        "Ticker": p_ticker, "Category": p_cat, "Avg Cost": p_cost, "Qty": p_qty
                    })
                    if p_ticker in st.session_state.watchlist:
                        st.session_state.watchlist.remove(p_ticker)
                    st.success(f"Added {p_ticker}!")
                    st.rerun()

        st.subheader("Add to Watchlist")
        with st.form("add_watch"):
            w_ticker = st.text_input("Ticker").upper()
            if st.form_submit_button("Add Watchlist"):
                if w_ticker and w_ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(w_ticker)
                    st.success(f"Added {w_ticker}!")
                    st.rerun()

    with tab_remove:
        st.subheader("Sell / Remove Position")
        current_holdings = [f"{item['Ticker']} ({item['Category']})" for item in st.session_state.portfolio]
        if current_holdings:
            to_remove = st.selectbox("Select Position to Remove", current_holdings)
            if st.button("🗑️ Confirm Remove Position"):
                ticker_to_remove = to_remove.split(" ")[0]
                st.session_state.portfolio = [x for x in st.session_state.portfolio if x['Ticker'] != ticker_to_remove]
                st.warning(f"Removed {ticker_to_remove} from Portfolio.")
                st.rerun()
        else:
            st.info("Portfolio is empty.")

        st.divider()
        st.subheader("Remove from Watchlist")
        if st.session_state.watchlist:
            w_remove = st.selectbox("Select Ticker", st.session_state.watchlist)
            if st.button("🗑️ Confirm Remove Watchlist"):
                st.session_state.watchlist.remove(w_remove)
                st.warning(f"Removed {w_remove}.")
                st.rerun()

# --- 4. PRB Tier Mapping ---
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

# --- 5. Data Fetching ---
try:
    now = datetime.utcnow() + timedelta(hours=7) 
    target_date_str = now.strftime("%d %B %Y %H:%M:%S")

    port_tickers = [item['Ticker'] for item in st.session_state.portfolio]
    watchlist_tickers = st.session_state.watchlist
    all_tickers = list(set(port_tickers + watchlist_tickers))

    @st.cache_data(ttl=60, show_spinner="Fetching Real-time Market Data...") 
    def get_realtime_data(tickers_list):
        data_dict = {}
        try:
            if not tickers_list: return {}
            df_hist = yf.download(tickers_list, period="2y", group_by='ticker', auto_adjust=True, threads=True)
        except Exception as e:
            return {}

        for ticker in tickers_list:
            try:
                if len(tickers_list) > 1:
                    df_t = df_hist[ticker].copy()
                else:
                    df_t = df_hist.copy()

                df_t = df_t.dropna()
                if df_t.empty or len(df_t) < 200:
                    data_dict[ticker] = {"Price": 0, "PrevClose": 0, "EMA50": 0, "EMA200": 0, "RSI": 50, "Sell1": 0, "Sell2": 0}
                    continue

                current_price = df_t['Close'].iloc[-1]
                prev_close = df_t['Close'].iloc[-2]
                
                df_t['EMA50'] = df_t['Close'].ewm(span=50, adjust=False).mean()
                df_t['EMA200'] = df_t['Close'].ewm(span=200, adjust=False).mean()
                
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_t['RSI'] = 100 - (100 / (1 + rs))

                df_t['SMA20'] = df_t['Close'].rolling(window=20).mean()
                df_t['STD20'] = df_t['Close'].rolling(window=20).std()
                sell_r1 = (df_t['SMA20'] + (df_t['STD20'] * 2)).iloc[-1] 
                sell_r2 = df_t['Close'].iloc[-252:].max()

                data_dict[ticker] = {
                    "Price": current_price, "PrevClose": prev_close,
                    "EMA50": df_t['EMA50'].iloc[-1], "EMA200": df_t['EMA200'].iloc[-1], 
                    "RSI": df_t['RSI'].iloc[-1], "Sell1": sell_r1, "Sell2": sell_r2
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
        df['%Day Change'] = ((df['Current Price'] - df['PrevClose']) / df['PrevClose']) if df['PrevClose'].sum() > 0 else 0

        def get_levels_series(ticker, price):
            data = market_data.get(ticker, {})
            buy1 = data.get('EMA50', 0)
            buy2 = data.get('EMA200', 0)
            sell1 = data.get('Sell1', 0)
            sell2 = data.get('Sell2', 0)
            
            diff_s1 = (price - buy1) / buy1 if buy1 > 0 else 0
            upside = (sell1 - price) / price if price > 0 else 0
            
            return pd.Series([buy1, buy2, sell1, sell2, diff_s1, upside], 
                            index=['Buy Lv.1', 'Buy Lv.2', 'Sell Lv.1', 'Sell Lv.2', 'Diff S1', 'Upside'])

        tech_cols = df.apply(lambda x: get_levels_series(x['Ticker'], x['Current Price']), axis=1)
        df = pd.concat([df, tech_cols], axis=1)

        total_value = df['Value USD'].sum() + cash_balance_usd
        total_gain = df['Total Gain USD'].sum()
        total_day_change = df['Day Change USD'].sum()
        total_invested = df['Total Cost'].sum()
    else:
        total_value = cash_balance_usd
        total_gain = 0
        total_day_change = 0
        total_invested = 0

    # --- 7. Styling Functions ---
    def color_text(val):
        if isinstance(val, (int, float)): return 'color: #28a745' if val >= 0 else 'color: #dc3545'
        return ''
    
    def color_diff_s1_logic(val):
        if isinstance(val, (int, float)):
            if val < 0: return 'color: #28a745; font-weight: bold;' 
            elif 0 <= val <= 0.02: return 'color: #90EE90;' 
            else: return 'color: #dc3545;' 
        return ''

    def color_rsi(val):
        try:
            v = float(val)
            if v >= 70: return 'color: #dc3545; font-weight: bold;'
            if v <= 30: return 'color: #28a745; font-weight: bold;'
        except: pass
        return ''

    def format_arrow(val):
        symbol = "⬆️" if val > 0 else "⬇️" if val < 0 else "➖"
        return f"{val:+.2%} {symbol}"

    def color_tier(val):
        if val == "S+": return 'color: #ffd700; font-weight: bold;' 
        if val == "S": return 'color: #c0c0c0; font-weight: bold;' 
        if "A" in str(val): return 'color: #cd7f32; font-weight: bold;' 
        return ''

    def highlight_row(s):
        try:
            if "IN ZONE" in str(s['Signal']): return ['background-color: rgba(40, 167, 69, 0.4)'] * len(s)
            elif "ALERT" in str(s['Signal']): return ['background-color: rgba(40, 167, 69, 0.2)'] * len(s)
            elif "PROFIT" in str(s['Signal']): return ['background-color: rgba(220, 53, 69, 0.2)'] * len(s)
        except: pass
        return [''] * len(s)

    # --- 8. UI Display ---
    st.title("🔭 My Portfolio & Watchlist") 
    st.caption(f"Last Update (BKK Time): {target_date_str} | Data Source: Yahoo Finance")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Value (USD)", f"${total_value:,.2f}", f"≈฿{total_value*33:,.0f}")
    c2.metric("🌊 Cash Flow", f"${cash_balance_usd:,.2f}", "Ready to Sniper")
    c3.metric("📈 Unrealized G/L", f"${total_gain:,.2f}", f"Invested: ${total_invested:,.0f}")
    c4.metric("📅 Day Change", f"${total_day_change:+.2f}", f"{(total_day_change/total_invested*100) if total_invested else 0:+.2f}%")

    st.markdown("---")

    col_mid_left, col_mid_right = st.columns([2, 1])
    with col_mid_left:
        st.subheader("ℹ️ Info") 
        with st.expander("🧠 Strategy: EMA Indicator & Diff S1 & RSI Coloring", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("""
                **📊 EMA Indicator Levels (Real-time):**
                * **Buy Lv.1 (EMA 50):** จุดเข้าซื้อตามเทรนด์ (Sniper Zone)
                * **Buy Lv.2 (EMA 200):** จุดรับของถูก (Deep Value / Floor)
                * **Sell Lv.1:** Upper Bollinger Band (แนวต้านระยะสั้น)
                * **Sell Lv.2:** 52-Week High (จุดสูงสุดเดิม)
                """)
            with c2:
                st.markdown("""
                **🎯 วิธีอ่านค่า Diff S1 แบบ Sniper:**
                * **ค่าติดลบ (< 0%):** ✅ **IN ZONE** (ของถูก) - **สีเขียวเข้ม**
                * **ค่าบวกเล็กน้อย (0% ถึง +2.0%):** 🟢 **ALERT** (เตรียมยิง) - **สีเขียวอ่อน**
                * **ค่าบวกเยอะๆ (> +2.0%):** ➖ **Wait** (แพงไป) - **สีแดง**
                """)
            with c3:
                st.markdown("""
                **🎨 RSI Coloring:**
                * **< 30:** **สีเขียว** (Oversold / น่าซื้อ)
                * **> 70:** **สีแดง** (Overbought / น่าขาย)
                """)
        
        # [NEW TITLE HERE]
        with st.expander("📅 Weekly Analysis & Notes : https://web.facebook.com/chaodoi.diary : ปฏิทินข้อมูลเศรษฐกิจที่สำคัญและการรายงานผลประกอบการที่น่าสนใจในสัปดาห์นี้", expanded=True):
            tab_view, tab_edit = st.tabs(["👁️ View", "✏️ Edit"])
            
            with tab_view:
                st.markdown(st.session_state.weekly_note)
            
            with tab_edit:
                st.info("คุณสามารถแก้ไข เพิ่ม หรือลบข้อความวิเคราะห์ได้ที่นี่ครับ")
                new_note = st.text_area("Note Editor:", value=st.session_state.weekly_note, height=250)
                if st.button("💾 Save Notes"):
                    st.session_state.weekly_note = new_note
                    st.success("บันทึกข้อมูลเรียบร้อย!")
                    st.rerun()

    with col_mid_right:
        st.subheader("📊 Asset Allocation (Including Cash)")
        
        if not df.empty:
            labels = list(df['Ticker']) + ['CASH 💵']
            values = list(df['Value USD']) + [cash_balance_usd]
        else:
            labels = ['CASH 💵']
            values = [cash_balance_usd]

        colors = ['#333333', '#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#7f7f7f', '#bcbd22', '#17becf']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=.5, marker_colors=colors, 
            textinfo='label+percent', textposition='inside', textfont=dict(size=16, color='white')
        )])
        fig_pie.update_layout(
            margin=dict(t=20, b=20, l=20, r=20), height=350, showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=14)),
            annotations=[dict(text=f'Total<br><b>${total_value:,.0f}</b>', x=0.5, y=0.5, font_size=24, showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    col_bot_left, col_bot_right = st.columns(2) 

    # --- LEFT SIDE: Portfolio (Filtered by Category) ---
    with col_bot_left:
        # Growth Engine
        st.subheader("🚀 Growth Engine") 
        if not df.empty:
            df_growth = df[df['Category'] == 'Growth'].copy()
            st.dataframe(
                df_growth.style.format({
                    "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                    "Diff S1": "{:+.1%}", "% P/L": format_arrow, "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                    "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Sell Lv.1": "${:.0f}"
                })
                .map(color_text, subset=['% P/L', 'Total Gain USD', 'Upside'])
                .map(color_diff_s1_logic, subset=['Diff S1']),
                column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "% P/L", "Current Price", "Value USD", "Total Gain USD", "Upside", "Diff S1", "Buy Lv.1", "Sell Lv.1"],
                column_config={
                    "Current Price": "Price", "% P/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)",
                    "Buy Lv.1": "Buy Lv.1", "Sell Lv.1": "Sell Lv.1", "Upside": st.column_config.Column("Upside", help="Gap to Sell Lv.1")
                },
                hide_index=True, use_container_width=True
            )
        else:
            st.info("No Growth stocks.")

        # Defensive Wall
        st.subheader("🛡️ Defensive Wall") 
        if not df.empty:
            df_defensive = df[df['Category'] == 'Defensive'].copy()
            st.dataframe(
                df_defensive.style.format({
                    "Qty": "{:.4f}", "Avg Cost": "${:.2f}", "Total Cost": "${:,.2f}", "Current Price": "${:.2f}",
                    "Diff S1": "{:+.1%}", "% P/L": format_arrow, "Value USD": "${:,.2f}", "Total Gain USD": "${:,.2f}",
                    "Upside": "{:+.1%}", "Buy Lv.1": "${:.0f}", "Sell Lv.1": "${:.0f}"
                })
                .map(color_text, subset=['% P/L', 'Total Gain USD', 'Upside'])
                .map(color_diff_s1_logic, subset=['Diff S1']),
                column_order=["Ticker", "Company", "Qty", "Avg Cost", "Total Cost", "% P/L", "Current Price", "Value USD", "Total Gain USD", "Upside", "Diff S1", "Buy Lv.1", "Sell Lv.1"],
                column_config={
                    "Current Price": "Price", "% P/L": "% Total", "Value USD": "Value ($)", "Total Gain USD": "Total Gain ($)",
                    "Buy Lv.1": "Buy Lv.1", "Sell Lv.1": "Sell Lv.1", "Upside": st.column_config.Column("Upside", help="Gap to Sell Lv.1")
                },
                hide_index=True, use_container_width=True
            )
        else:
            st.info("No Defensive stocks.")

    # --- RIGHT SIDE: Watchlist ---
    with col_bot_right:
        st.subheader("🎯 Sniper Watchlist (Fractional Unlocked)")
        
        watchlist_data = []
        for t in sorted(list(set(st.session_state.watchlist))): 
            data = market_data.get(t, {})
            price = data.get('Price', 0)
            prev = data.get('PrevClose', 0)
            pct_change = (price - prev) / prev if prev > 0 else 0
            
            buy1 = data.get('EMA50', 0)
            sell1 = data.get('Sell1', 0)
            rsi = data.get('RSI', 50)
            
            diff_s1 = (price - buy1)/buy1 if buy1 > 0 else 9.99
            upside = (sell1 - price)/price if price > 0 else 0
            
            signal = "4. Wait" 
            if diff_s1 < 0 and price > 0: signal = "1. ✅ IN ZONE"
            elif 0 <= diff_s1 <= 0.02 and price > 0: signal = "2. 🟢 ALERT"
            elif price >= sell1: signal = "5. 🔴 PROFIT"
            else: signal = "3. ➖ Wait"
            
            watchlist_data.append({
                "Tier": prb_tiers.get(t, "-"), "Ticker": t, "Price": price, "% Day": pct_change, "Signal": signal, 
                "Diff S1": diff_s1, "RSI": rsi, "Upside": upside,
                "Buy Lv.1": data.get('EMA50', 0), "Buy Lv.2": data.get('EMA200', 0), 
                "Sell Lv.1": data.get('Sell1', 0), "Sell Lv.2": data.get('Sell2', 0),
                "Display Signal": signal.split(". ")[1] 
            })
        
        df_watch = pd.DataFrame(watchlist_data)
        if not df_watch.empty:
            df_watch = df_watch.sort_values(by=["Signal", "Diff S1"], ascending=[True, True])

            st.dataframe(
                df_watch.style.format({
                    "Price": "${:.2f}", "% Day": format_arrow, "Diff S1": "{:+.1%}", "RSI": "{:.0f}", "Upside": "{:+.1%}",
                    "Buy Lv.1": "${:.0f}", "Buy Lv.2": "${:.0f}", "Sell Lv.1": "${:.0f}", "Sell Lv.2": "${:.0f}"
                })
                .apply(highlight_row, axis=1)
                .map(color_diff_s1_logic, subset=['Diff S1'])
                .map(color_tier, subset=['Tier'])
                .map(color_rsi, subset=['RSI'])
                .map(color_text, subset=['Upside']), 
                column_config={
                    "Display Signal": st.column_config.Column("Status", width="medium"),
                    "Tier": st.column_config.Column("Tier", width="small"),
                    "Ticker": st.column_config.Column("Symbol", width="small"),
                    "Price": st.column_config.Column("Price", width="small"),
                    "% Day": st.column_config.Column("% Day", width="small"),
                    "Diff S1": st.column_config.Column("Diff S1", help="Distance to EMA 50"),
                    "Upside": st.column_config.Column("Upside", help="Gap to Sell Lv.1"),
                    "RSI": st.column_config.Column("RSI", help="RSI (14)"),
                    "Buy Lv.1": st.column_config.Column("Buy (EMA50)"),
                    "Buy Lv.2": st.column_config.Column("Buy (EMA200)"),
                    "Sell Lv.1": st.column_config.Column("Sell (R1)"),
                    "Sell Lv.2": st.column_config.Column("Sell (R2)"),
                },
                column_order=["Display Signal", "Tier", "Ticker", "Price", "% Day", "Upside", "Diff S1", "RSI", "Buy Lv.1", "Buy Lv.2", "Sell Lv.1", "Sell Lv.2"],
                hide_index=True, use_container_width=True
            )
        else:
            st.info("Watchlist is empty.")

except Exception as e:
    st.error(f"System Error: {e}")
