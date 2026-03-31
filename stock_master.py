import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎設定
st.set_page_config(page_title="AI 股市戰情室", layout="wide", initial_sidebar_state="collapsed")

# --- 輔助函式：台股名稱對照表 (確保 100% 顯示中文) ---
def get_tw_stock_name(symbol):
    tw_names = {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
        "2303": "聯電", "2881": "富邦金", "2882": "國泰金", "2412": "中華電",
        "1301": "台塑", "1303": "南亞", "2603": "長榮", "2609": "陽明",
        "6175": "立敦", "2382": "廣達", "2357": "華碩", "3008": "大立光",
        "3231": "緯創", "2376": "技嘉", "2618": "長榮航", "2610": "華航"
    }
    return tw_names.get(symbol, None)

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
def get_fundamental_data(stock_input, final_ticker):
    try:
        ticker = yf.Ticker(final_ticker)
        info = ticker.info
        # 優先找對照表，再找 API 欄位
        tw_name = get_tw_stock_name(stock_input)
        name = tw_name if tw_name else (info.get("shortName") or info.get("longName") or stock_input)
        
        return {
            "name": name,
            "PE": info.get("trailingPE", "N/A"),
            "PB": info.get("priceToBook", "N/A"),
            "ROE": info.get("returnOnEquity", "N/A")
        }
    except:
        return {"name": stock_input, "PE": "N/A", "PB": "N/A", "ROE": "N/A"}

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

# --- 側邊欄：完整還原原本四層篩選機制 ---
with st.sidebar:
    st.title("🌐 全球股票搜尋")
    stock_input = st.text_input("輸入代碼 (如: 2330, NVDA)", value="2330").strip().upper()
    st.divider()
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
    fundamentals = get_fundamental_data(stock_input, final_ticker)
    latest_c = float(df_main['Close'].iloc[-1])
    open_p = float(df_main['Open'].iloc[-1])
    last_v = float(df_main['Volume'].iloc[-1])
    avg_v = float(df_main['Volume'].mean())
    ma20_now = df_main['MA20'].iloc[-1] if 'MA20' in df_main else 0

    # 顯示股票名稱
    st.title(f"🚀 {fundamentals['name']} ({final_ticker})")

    # 綜合評分 (還原原本 score 邏輯)
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
        if score >= 80: st.success("**【極力推薦】現正處於多頭攻擊態勢！** 價格站穩開盤且有量能支撐，位階安全。")
        elif score >= 60: st.warning("**【適合小量試單】目前處於震盪偏多局面。** 有動能但尚未全面爆發。")
        elif score >= 40: st.info("**【保守觀望】趨勢不明朗，不建議急著進場。** 建議等回檔支撐位再考慮。")
        else: st.error("**【嚴禁接刀】目前空方勢力強大。** 股價跌破開盤且低於月線，切勿貿然進場。")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("市價", f"{latest_c:.2f}")
        c2.metric("漲跌幅", f"{((latest_c-open_p)/open_p)*100:.2f}%")
        
        pe_val = fundamentals['PE']
        pe_display = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
        pb_val = fundamentals['PB']
        pb_display = f"{pb_val:.2f}" if isinstance(pb_val, (int, float)) else "N/A"
        
        c3.metric("本益比 (PE)", pe_display)
        c4.metric("股價淨值 (PB)", pb_display)

    st.divider()

    # 2. 下方雙介面：將您要求的內容完整保留在主畫面
    col_main_content = st.container()
    
    with col_main_content:
        st.subheader("⚡️ 當沖/基本面評估")
        trend_status = "🔴 偏多勢" if latest_c > open_p else "🟢 偏空勢"
        st.info(f"今日趨勢：{trend_status} | 開盤參考：{open_p:.2f}")
        
        # 基本面體檢
        roe_val = f"{fundamentals['ROE']*100:.1f}%" if isinstance(fundamentals['ROE'], (int, float)) else "N/A"
        st.write(f"**基本面體檢：** ROE {roe_val}")
        
        # 歷史行情表格 (完整還原 Open, High, Low, Close, Volume)
        disp_df = df_main[['Open', 'High', 'Low', 'Close', 'Volume']].tail(5).copy()
        disp_df['Volume'] = disp_df['Volume'].apply(format_vol_unit)
        st.dataframe(disp_df, use_container_width=True)
        
        # 位階建議
        st.markdown("🚩 **位階建議**")
        st.write(f"📈 建議支撐：{latest_c*0.98:.2f}")
        st.write(f"📉 建議壓力：{latest_c*1.03:.2f}")

else:
    st.error("❌ 無法抓取該代碼數據。")
