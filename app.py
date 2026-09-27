import streamlit as st
import requests
from binance.spot import Spot as Client

st.set_page_config(page_title="Kripto Arbitraj Botu", page_icon="⚡", layout="wide")

st.title("⚡ Kripto Üçgen Arbitraj Takibi")

# --- TELEGRAM AYARLARI ---
st.sidebar.header("📱 Telegram Bildirim Ayarları")
telegram_token = st.sidebar.text_input("Bot Token", type="password", help="BotFather'dan aldığınız token")
telegram_chat_id = st.sidebar.text_input("Chat ID", help="userinfobot'tan aldığınız ID")
min_profit = st.sidebar.number_input("Minimum Kâr Eşiği (%)", value=0.05, step=0.01)

def send_telegram_message(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            st.error(f"Telegram mesajı gönderilemedi: {e}")

# Binance Client
client = Client()

try:
    # Fiyat çekme
    p1 = float(client.ticker_price("BTCUSDT")['price'])
    p2 = float(client.ticker_price("ETHBTC")['price'])
    p3 = float(client.ticker_price("ETHUSDT")['price'])

    # Üçgen arbitraj hesabı
    final_usdt = (1 / p1) * (1 / p2) * p3
    profit = (final_usdt - 1) * 100

    # Ekran Bilgisi
    col1, col2, col3 = st.columns(3)
    col1.metric("BTC / USDT", f"${p1:,.2f}")
    col2.metric("ETH / BTC", f"{p2:.6f}")
    col3.metric("ETH / USDT", f"${p3:,.2f}")

    st.write("---")

    if profit > min_profit:
        msg = f"🚀 **Kârlı Fırsat Yakalandı!**\n\n**Tahmini Kâr:** %{profit:.4f}\n• BTC/USDT: ${p1:,.2f}\n• ETH/BTC: {p2:.6f}\n• ETH/USDT: ${p3:,.2f}"
        st.success(f"🔥 Kârlı Fırsat! Tahmini Kâr: %{profit:.4f}")
        
        # Telegram Mesajı Gönder
        send_telegram_message(telegram_token, telegram_chat_id, msg)
    else:
        st.warning(f"Kârlı fırsat yok. Mevcut Durum: %{profit:.4f}")

except Exception as e:
    st.error(f"Hata oluştu: {e}")
