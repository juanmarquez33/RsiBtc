import os
import requests
import pandas as pd
import yfinance as yf

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def calculate_rsi(df, window=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_all_tickers():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        df_sp500 = tables[0]
        tickers = df_sp500['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        print(f"Error obteniendo S&P 500 de Wikipedia: {e}")
        tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'NVDA']

    crypto_tickers = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD']
    return list(set(tickers + crypto_tickers))

def scan_market():
    tickers = get_all_tickers()
    print(f"Iniciando escaneo de {len(tickers)} activos...")

    tf_configs = {
        '1D': {'interval': '1d', 'period': '60d'},
        '1H': {'interval': '60m', 'period': '30d'}
    }

    # Para probar con pocos activos primero si quieres, o con todos:
    for ticker in tickers[:15]:  # Probamos con los primeros 15 para ver la consola rápido
        for tf, config in tf_configs.items():
            try:
                df = yf.download(ticker, interval=config['interval'], period=config['period'], progress=False)
                if df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df = calculate_rsi(df)
                if len(df) < 15:
                    continue

                last = df.iloc[-1]
                price = float(last['Close'])
                rsi = float(last['RSI'])
                
                print(f"[{ticker}] ({tf}) -> Precio: {price}, RSI: {rsi:.2f}")

                if rsi < 30:
                    msg = (
                        f"🟢 *¡ALERTA DE SOBREVENTA ({tf})!* 🟢\n\n"
                        f"📊 *Activo:* `{ticker}`\n"
                        f"💵 *Precio Actual:* `${price:,.2f}`\n"
                        f"📉 *RSI:* `{rsi:.1f}` (Zona de sobreventa < 30)"
                    )
                    send_telegram_message(msg)
                    print(f"¡ALERTA ENVIADA para {ticker} en {tf} con RSI {rsi:.1f}!")
            except Exception as e:
                print(f"Error procesando {ticker} en {tf}: {e}")

    print("Escaneo de prueba finalizado.")

if __name__ == "__main__":
    scan_market()
