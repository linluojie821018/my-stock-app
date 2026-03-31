import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="AI 股市戰情室", layout="wide")

# --- 輔助函式：單位轉換 ---
def format_vol_unit(vol):
    try:
        v = float(vol)
        if v >= 100000000: return f"{v / 100000000:.2f} 億"
        elif v >= 10000: return f"{v / 10000:.2f} 萬"
        else: return f"{int(v)}"
    except: return "N/A"

# --- 核心數據抓取 ---
@st.cache_data(ttl=3600)
def get_fundamental_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "PE": info.get("trailingPE", "N/A"),
            "PB": info.get("priceToBook", "N/A"),
            "ROE": info.get("returnOnEquity", "N/A")
        }
    except:
        return {"PE": "N/A", "PB": "N/A", "ROE": "N/A"}

def get_stock_data(symbol, interval="1d"):
    p_map = {"5m":"60d","15m":"60d","30m":"60d","60m":"730d","1d":"2y","1wk":"max","1mo":"max"}
    period = p_map.get(interval, "2y")
    
    def fetch_api(t_code):
        try:
            df = yf.download(t_code, period=period, interval=interval, progress=False, auto_adjust=True)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if interval == "1d":
                    df['MA20'] = df['Close'].rolling(window=20).mean()
                return df
            return pd.DataFrame()
        except: return pd.DataFrame()

    if symbol.isdigit():
        for suffix in [".TW", ".TWO"]:
            t = f"{symbol}{suffix}"
            data = fetch_api(t)
            if not data.empty: return data, t
        return pd.DataFrame(), symbol
    else:
        return fetch_api(symbol), symbol

# --- 側邊欄：優化為選股指標指南 ---
with st.sidebar:
    st.title("🌐 全球股票搜尋")
    stock_input = st.text_input("輸入代碼 (如: 2330, NVDA)", value="2330").strip().upper()
    st.divider()
    # 替換為選股指標說明
    st.write("🎯 **漏斗式選股指標**")
    with st.expander("第一層：流動性", expanded=True):
        st.caption("● 成交量 > 1,000張\n● 確保買得到、賣得掉")
    with st.expander("第二層：基本面"):
        st.caption("● ROE > 10%\n● 避開虧損地雷股")
    with st.expander("第三層：評價面"):
        st.caption("● PE 位於歷史低位\n● 判斷現在是否太貴")
    with st.expander("第四層：技術面"):
        st.caption("● 股價站在月線(20MA)之上\n● 找尋好的切入點")

# --- 執行主邏輯 ---
df_main, final_ticker = get_stock_data(stock_input, interval="1d")

if not df_main.empty:
    fundamentals = get_fundamental_data(final_ticker)
    latest_c = float(df_main['Close'].iloc[-1])
    open_p = float(df_main['Open'].iloc[-1])
    last_v = float(df_main['Volume'].iloc[-1])
    avg_v = float(df_main['Volume'].mean())
    ma20_now = df_main['MA20'].iloc[-1] if 'MA20' in df_main else 0

    # 綜合評分邏輯
    score = 0
    if latest_c > open_p: score += 40
    if last_v > avg_v: score += 40
    if ma20_now > 0 and latest_c > ma20_now: score += 20

    # 1. 頂部儀表板
    col_g, col_txt = st.columns([1, 1.5])
    with col_g:
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = score,
            title = {'text': "🎯 AI 綜合評分", 'font': {'size': 20}},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#FF4B4B"},
                     'steps': [{'range': [0, 40], 'color': "#E8E8E8"},
                               {'range': [40, 75], 'color': "#FFE082"},
                               {'range': [75, 100], 'color': "#81C784"}]}))
        fig_g.update_layout(height=280, margin=dict(l=20, r=20, b=0, t=40))
        st.plotly_chart(fig_g, use_container_width=True)

    with col_txt:
        st.write("### 📋 投資診斷報告")
        # 新增白話建議邏輯
        if score >= 80:
            st.success("**【極力推薦】現正處於多頭攻擊態勢！** 價格站穩開盤且有量能支撐，月線位階安全，是理想的切入時機。")
        elif score >= 60:
            st.warning("**【適合小量試單】目前處於震盪偏多局面。** 有動能但尚未全面爆發，建議等突破壓力位後再加碼。")
        elif score >= 40:
            st.info("**【保守觀望】趨勢不明朗，不建議急著進場。** 目前多空拉鋸，建議等股價回檔支撐位且量縮止跌再考慮。")
        else:
            st.error("**【嚴禁接刀】目前空方勢力強大。** 股價跌破開盤且低於月線，下方支撐尚未站穩，切勿貿然進場。")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("市價", f"{latest_c:.2f}")
        c2.metric("漲跌幅", f"{((latest_c-open_p)/open_p)*100:.2f}%")
        c3.metric("本益比 (PE)", f"{fundamentals['PE'] if isinstance(fundamentals['PE'], (int, float)) else 'N/A':.2f}")
        c4.metric("股價淨值 (PB)", f"{fundamentals['PB'] if isinstance(fundamentals['PB'], (int, float)) else 'N/A':.2f}")

    st.divider()

    # 2. 下方雙介面
    col_left, col_right = st.columns([1, 1.3])
    with col_left:
        st.subheader("⚡️ 當沖/基本面評估")
        trend_status = "🔴 偏多勢" if latest_c > open_p else "🟢 偏空勢"
        st.info(f"今日趨勢：{trend_status} | 開盤參考：{open_p:.2f}")
        
        roe_val = f"{fundamentals['ROE']*100:.1f}%" if isinstance(fundamentals['ROE'], (int, float)) else "N/A"
        st.write(f"**基本面體檢：** ROE {roe_val}")
        
        disp_df = df_main[['Open', 'High', 'Low', 'Close', 'Volume']].tail(5).copy()
        disp_df['Volume'] = disp_df['Volume'].apply(format_vol_unit)
        st.dataframe(disp_df, use_container_width=True)
        
        st.markdown("🚩 **位階建議**")
        st.write(f"📈 建議支撐：{latest_c*0.98:.2f}")
        st.write(f"📉 建議壓力：{latest_c*1.03:.2f}")

    with col_right:
        st.subheader("🎯 Yahoo 風格 K 線圖")
        t_unit = st.radio("切換週期：", ["5m", "15m", "30m", "60m", "1d", "1wk", "1mo"], index=4, horizontal=True)
        plot_df = df_main if t_unit == "1d" else get_stock_data(stock_input, interval=t_unit)[0]
        
        if not plot_df.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name="K線", increasing_line_color='#FF4B4B', decreasing_line_color='#00B050'), row=1, col=1)
            if 'MA20' in plot_df:
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA20'], line=dict(color='#2196F3', width=1.5), name="20MA"), row=1, col=1)
            v_colors = ['#FF4B4B' if c >= o else '#00B050' for c, o in zip(plot_df['Close'], plot_df['Open'])]
            fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume'], marker_color=v_colors, opacity=0.8), row=2, col=1)
            fig.update_layout(height=500, margin=dict(l=0, r=0, b=0, t=0), template="plotly_white", xaxis_rangeslider_visible=False, dragmode='pan', hovermode='x unified', showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})