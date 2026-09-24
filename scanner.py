import os
import requests
import pandas as pd
import yfinance as yf

# ================= CONFIGURACIÓN DE TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def send_telegram_message(message):
    """Envía el reporte al chat de Telegram configurado en GitHub Secrets."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def calculate_rsi(df, window=14):
    """Calcula el RSI usando el método de Wilder (igual que TradingView)."""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_all_tickers():
    """Obtiene el S&P 500, criptos y las acciones adicionales solicitadas."""
    tickers = []
    
    # 1. Obtener S&P 500 desde Wikipedia
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        df_sp500 = tables[0]
        tickers = df_sp500['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        print(f"Error obteniendo S&P 500: {e}")
        tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'NVDA', 'META', 'TSLA']

    # 2. Top 5 Criptomonedas
    crypto_tickers = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD']
    
    # 3. Acciones adicionales personalizadas (incluyendo TSM, BRK-B y ASML)
    custom_tickers = [
        'UBER',   # Uber
        'BAC',    # Bank of America
        'MU',     # Micron Technology
        'V',      # Visa
        'MA',     # Mastercard
        'UNH',    # UnitedHealth Group
        'LLY',    # Eli Lilly
        'AVGO',   # Broadcom
        'MCD',    # McDonald's
        'KO',     # Coca-Cola
        'MELI',   # MercadoLibre
        'NU',     # Nubank
        'TSM',    # Taiwan Semiconductor Manufacturing
        'BRK-B',  # Berkshire Hathaway
        'ASML'    # ASML Holding
    ]
    
    # Combinar todo sin repetir símbolos
    return list(set(tickers + crypto_tickers + custom_tickers))

def process_timeframe(tickers, tf, interval, period):
    """Procesa el mercado para una temporalidad específica y retorna el Top 10."""
    print(f"Escaneando temporalidad {tf}...")
    resultados = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, interval=interval, period=period, progress=False)
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

            if pd.notna(rsi):
                resultados.append({
                    'ticker': ticker,
                    'price': price,
                    'rsi': rsi
                })
        except Exception:
            pass

    if not resultados:
        return []

    # Ordenar de menor a mayor RSI y tomar los 10 más bajos
    resultados_ordenados = sorted(resultados, key=lambda x: x['rsi'])
    return resultados_ordenados[:10]

def scan_market():
    """Ejecuta el escaneo para temporalidad Diaria (1D) y de 1 Hora (1H)."""
    tickers = get_all_tickers()
    print(f"Iniciando escaneo de {len(tickers)} activos...")

    # 1. Escaneo Diario (1D)
    top_1d = process_timeframe(tickers, '1D', interval='1d', period='60d')
    if top_1d:
        msg_1d = "📉 *TOP 10 ACTIVOS CON RSI MÁS BAJO (Diario - 1D)* 📉\n\n"
        for i, item in enumerate(top_1d, 1):
            msg_1d += (
                f"*{i}. `{item['ticker']}`*\n"
                f"   💵 Precio: `${item['price']:,.2f}`\n"
                f"   📉 RSI: `{item['rsi']:.1f}`\n\n"
            )
        send_telegram_message(msg_1d)

    # 2. Escaneo de 1 Hora (1H)
    top_1h = process_timeframe(tickers, '1H', interval='60m', period='30d')
    if top_1h:
        msg_1h = "⏱ *TOP 10 ACTIVOS CON RSI MÁS BAJO (1 Hora - 1H)* ⏱\n\n"
        for i, item in enumerate(top_1h, 1):
            msg_1h += (
                f"*{i}. `{item['ticker']}`*\n"
                f"   💵 Precio: `${item['price']:,.2f}`\n"
                f"   📉 RSI: `{item['rsi']:.1f}`\n\n"
            )
        send_telegram_message(msg_1h)

    print("Escaneo completo de 1D y 1H finalizado y enviado.")

if __name__ == "__main__":
    scan_market()
