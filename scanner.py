import os
import requests
import pandas as pd
import yfinance as yf

# ================= CONFIGURACIÓN DE TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def send_telegram_message(message):
    """Envía la alerta al chat de Telegram configurado en GitHub Secrets."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Advertencia: Credenciales de Telegram no configuradas.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Error al enviar Telegram: {response.text}")
    except Exception as e:
        print(f"Error de conexión con Telegram: {e}")

def calculate_rsi(df, window=14):
    """Calcula el RSI de 14 períodos."""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def analyze_bitcoin_timeframes():
    """Analiza Bitcoin en temporalidades 1D, 4H y 1H buscando sobreventa (RSI < 30)."""
    ticker = 'BTC-USD'
    print(f"Iniciando análisis de {ticker}...")

    # 1. Temporalidad Diaria (1D)
    try:
        df_1d = yf.download(ticker, interval='1d', period='60d', progress=False)
        if not df_1d.empty:
            if isinstance(df_1d.columns, pd.MultiIndex):
                df_1d.columns = df_1d.columns.get_level_values(0)
            df_1d = calculate_rsi(df_1d)
            
            last_1d = df_1d.iloc[-1]
            price_1d = float(last_1d['Close'])
            rsi_1d = float(last_1d['RSI'])
            
            print(f"[1D] Precio: ${price_1d:,.2f} | RSI: {rsi_1d:.1f}")
            if rsi_1d < 30:
                msg = (
                    f"🟢 *¡ALERTA DE SOBREVENTA EN BITCOIN (1D)!* 🟢\n\n"
                    f"🪙 *Activo:* `BTC-USD`\n"
                    f"⏱ *Temporalidad:* `Diaria (1D)`\n"
                    f"💵 *Precio Actual:* `${price_1d:,.2f}`\n"
                    f"📊 *RSI:* `{rsi_1d:.1f}` (Zona de sobreventa < 30)"
                )
                send_telegram_message(msg)
    except Exception as e:
        print(f"Error en temporalidad 1D: {e}")

    # 2. Temporalidades Intradía (1H y 4H basadas en datos de 1 hora)
    try:
        df_1h = yf.download(ticker, interval='60m', period='60d', progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex):
                df_1h.columns = df_1h.columns.get_level_values(0)

            # --- Evaluar 1 Hora (1H) ---
            df_1h_calc = calculate_rsi(df_1h.copy())
            last_1h = df_1h_calc.iloc[-1]
            price_1h = float(last_1h['Close'])
            rsi_1h = float(last_1h['RSI'])
            
            print(f"[1H] Precio: ${price_1h:,.2f} | RSI: {rsi_1h:.1f}")
            if rsi_1h < 30:
                msg = (
                    f"🟢 *¡ALERTA DE SOBREVENTA EN BITCOIN (1H)!* 🟢\n\n"
                    f"🪙 *Activo:* `BTC-USD`\n"
                    f"⏱ *Temporalidad:* `1 Hora (1H)`\n"
                    f"💵 *Precio Actual:* `${price_1h:,.2f}`\n"
                    f"📊 *RSI:* `{rsi_1h:.1f}` (Zona de sobreventa < 30)"
                )
                send_telegram_message(msg)

            # --- Evaluar 4 Horas (4H) transformando las velas de 1H ---
            df_4h = df_1h.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

            df_4h_calc = calculate_rsi(df_4h)
            last_4h = df_4h_calc.iloc[-1]
            price_4h = float(last_4h['Close'])
            rsi_4h = float(last_4h['RSI'])
            
            print(f"[4H] Precio: ${price_4h:,.2f} | RSI: {rsi_4h:.1f}")
            if rsi_4h < 30:
                msg = (
                    f"🟢 *¡ALERTA DE SOBREVENTA EN BITCOIN (4H)!* 🟢\n\n"
                    f"🪙 *Activo:* `BTC-USD`\n"
                    f"⏱ *Temporalidad:* `4 Horas (4H)`\n"
                    f"💵 *Precio Actual:* `${price_4h:,.2f}`\n"
                    f"📊 *RSI:* `{rsi_4h:.1f}` (Zona de sobreventa < 30)"
                )
                send_telegram_message(msg)

    except Exception as e:
        print(f"Error en temporalidades intradía (1H/4H): {e}")

    print("Análisis de Bitcoin finalizado.")

if __name__ == "__main__":
    analyze_bitcoin_timeframes()
