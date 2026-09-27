import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Kripto Analiz & Arbitraj", page_icon="🚀", layout="wide")
st.title("🚀 Kripto Analiz ve Arbitraj Merkezi")

# Uygulamayı 2 Sekmeye (Tab) Bölüyoruz
tab1, tab2 = st.tabs(["📈 Canlı Grafik & Sinyal", "🧮 Üçgen Arbitraj Simülatörü"])

# --- ORTAK AYARLAR (SOL MENÜ) ---
st.sidebar.header("⚙️ Genel Ayarlar")
auto_refresh = st.sidebar.checkbox("🔄 Otomatik Yenile (10 sn)", value=True)
st.sidebar.markdown("---")

# --- Binance US API Fonksiyonları (IP Engeli Aşmak İçin) ---
@st.cache_data(ttl=5) # 5 saniyede bir tazelemeye izin ver
def get_klines(sym, intv):
    url = f"https://api.binance.us/api/v3/klines?symbol={sym}&interval={intv}&limit=100"
    res = requests.get(url, timeout=5).json()
    df = pd.DataFrame(res, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    return df

def get_price(symbol):
    url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return float(res.json()['price'])
    except:
        pass
    return None


# ==========================================
# SEKME 1: GRAFİK VE SİNYAL BOTU
# ==========================================
with tab1:
    st.sidebar.header("📊 Grafik Ayarları")
    symbol = st.sidebar.selectbox("Coin Seç", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT"])
    interval = st.sidebar.selectbox("Zaman Dilimi", ["1m", "5m", "15m", "1h", "4h", "1d"])
    indicators = st.sidebar.multiselect("İndikatör Ekle", ["Fibonacci", "RSI", "MACD"], default=["Fibonacci", "RSI"])

    try:
        df = get_klines(symbol, interval)
        current_price = df['close'].iloc[-1]

        st.subheader(f"{symbol} - Anlık Fiyat: ${current_price:,.2f}")
        
        col1, col2, col3 = st.columns(3)
        signal = "⚪ NÖTR"
        
        if "RSI" in indicators:
            df['RSI'] = RSIIndicator(df['close'], window=14).rsi()
            rsi_val = df['RSI'].iloc[-1]
            col1.metric("RSI (14)", f"{rsi_val:.2f}")
            if rsi_val < 30:
                signal = "🟢 GÜÇLÜ AL (Aşırı Satım)"
            elif rsi_val > 70:
                signal = "🔴 GÜÇLÜ SAT (Aşırı Alım)"

        if "MACD" in indicators:
            macd = MACD(df['close'])
            df['MACD'] = macd.macd()
            macd_val = df['MACD'].iloc[-1]
            col2.metric("MACD", f"{macd_val:.2f}")

        col3.info(f"**Sinyal Durumu:** {signal}")

        # Grafik Çizimi
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Fiyat"
        )])

        # Fibonacci Çizimi
        if "Fibonacci" in indicators:
            max_price, min_price = df['high'].max(), df['low'].min()
            diff = max_price - min_price
            fib_levels = {
                "Tepe": max_price,
                "0.236": max_price - 0.236 * diff,
                "0.382": max_price - 0.382 * diff,
                "0.500": max_price - 0.500 * diff,
                "0.618": max_price - 0.618 * diff,
                "Dip": min_price
            }
            for name, price in fib_levels.items():
                fig.add_hline(y=price, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                              annotation_text=f"Fib {name}: ${price:.2f}", annotation_position="top left")

        fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0, r=0, t=30, b=0))
        fig.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Grafik verisi çekilemedi: {e}")


# ==========================================
# SEKME 2: ÜÇGEN ARBİTRAJ SİMÜLATÖRÜ
# ==========================================
with tab2:
    st.sidebar.markdown("---")
    st.sidebar.header("🧮 Arbitraj Ayarları")
    start_capital = st.sidebar.number_input("Başlangıç (USDT)", value=1000.0, step=100.0)
    fee_rate = st.sidebar.number_input("Borsa Komisyonu (%)", value=0.1, step=0.01)

    st.markdown("💡 **Nasıl Çalışır?** Elimizdeki USDT ile sırasıyla **BTC -> ETH -> USDT** döngüsü yaparız. Döngü sonunda komisyonlar düşüldükten sonra para artıyorsa arbitraj kârlıdır.")
    
    try:
        p_btc_usdt = get_price("BTCUSDT")
        p_eth_btc = get_price("ETHBTC")
        p_eth_usdt = get_price("ETHUSDT")

        if p_btc_usdt and p_eth_btc and p_eth_usdt:
            c1, c2, c3 = st.columns(3)
            c1.metric("1. Adım: BTC/USDT", f"${p_btc_usdt:,.2f}")
            c2.metric("2. Adım: ETH/BTC", f"{p_eth_btc:.6f}")
            c3.metric("3. Adım: ETH/USDT", f"${p_eth_usdt:,.2f}")

            fee_multiplier = 1 - (fee_rate / 100)
            btc_bought = (start_capital / p_btc_usdt) * fee_multiplier
            eth_bought = (btc_bought / p_eth_btc) * fee_multiplier
            final_usdt = (eth_bought * p_eth_usdt) * fee_multiplier

            net_profit_usdt = final_usdt - start_capital
            net_profit_percent = (net_profit_usdt / start_capital) * 100

            st.write("---")
            rc1, rc2 = st.columns(2)
            rc1.metric(f"Başlangıç: {start_capital} USDT", f"Bitiş: {final_usdt:.4f} USDT", f"%{net_profit_percent:.4f}")
            
            if final_usdt > start_capital:
                st.success(f"🔥 KÂRLI FIRSAT YAKALANDI! Net Kâr: {net_profit_usdt:.4f} USDT")
            else:
                st.warning(f"❌ Kâr Yok. İşlem kesintileri yüzünden zarar ediliyor. Zarar: {net_profit_usdt:.4f} USDT")

    except Exception as e:
        st.error(f"Arbitraj verisi çekilemedi: {e}")

# ==========================================
# CANLI AKIŞ - OTOMATİK YENİLEME
# ==========================================
if auto_refresh:
    time.sleep(10) # 10 saniyede bir ekranı kendi kendine yeniler
    st.rerun()
