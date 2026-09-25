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

def calculate_indicators(df, window=14):
    """Calcula el RSI (Wilder) y la EMA de 21 periodos."""
    # 1. RSI (Wilder)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. EMA 21
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # 3. Promedio de Volumen (20 periodos)
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
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
    
    # 3. Acciones adicionales personalizadas
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
        'TSM',    # Taiwan Semiconductor
        'BRK-B',  # Berkshire Hathaway
        'ASML'    # ASML Holding
    ]
    
    return list(set(tickers + crypto_tickers + custom_tickers))

def process_timeframe(tickers, tf, interval, period):
    """Procesa el mercado para una temporalidad específica y retorna el Top 10 de RSI."""
    print(f"Escaneando temporalidad RSI {tf}...")
    resultados = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, interval=interval, period=period, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = calculate_indicators(df)
            if len(df) < 25:
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

    resultados_ordenados = sorted(resultados, key=lambda x: x['rsi'])
    return resultados_ordenados[:10]

def check_ema_breakouts(tickers):
    """Detecta activos que rompen la EMA de 21 al alza con buen volumen en gráfico diario (1D)."""
    print("Escaneando rupturas de EMA 21 con volumen...")
    breakouts = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, interval='1d', period='60d', progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = calculate_indicators(df)
            if len(df) < 25:
                continue

            # Datos vela anterior y vela actual
            prev_close = float(df['Close'].iloc[-2])
            prev_ema = float(df['EMA21'].iloc[-2])
            
            curr_close = float(df['Close'].iloc[-1])
            curr_ema = float(df['EMA21'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Vol_SMA20'].iloc[-1])

            # Condición de ruptura alcista: Estaba debajo/igual y cruzó arriba + Volumen mayor al promedio
            if prev_close <= prev_ema and curr_close > curr_ema and curr_vol > avg_vol:
                vol_increase = ((curr_vol / avg_vol) - 1) * 100
                breakouts.append({
                    'ticker': ticker,
                    'price': curr_close,
                    'ema': curr_ema,
                    'vol_inc': vol_increase
                })
        except Exception:
            pass

    # Si hay rupturas, enviamos un alerta especial
    if breakouts:
        msg = "🚀 *¡ALERTA DE RUPTURA EMA 21 CON VOLUMEN!* 🚀\n\n"
        for item in breakouts:
            msg += (
                f"🔥 *`{item['ticker']}`*\n"
                f"   💵 Precio: `${item['price']:,.2f}`\n"
                f"   📈 Cruce EMA 21: `${item['ema']:,.2f}`\n"
                f"   📊 Vol: `+{item['vol_inc']:.1f}%` sobre la media\n\n"
            )
        send_telegram_message(msg)
        print("Alertas de ruptura enviadas.")
    else:
        print("No se registraron rupturas de EMA 21 con volumen en esta ejecución.")

def scan_market():
    """Ejecuta todo el flujo del bot."""
    tickers = get_all_tickers()
    print(f"Iniciando escaneo completo de {len(tickers)} activos...")

    # 1. Escaneo Semanal (1W) RSI
    top_1w = process_timeframe(tickers, '1W', interval='1wk', period='2y')
    if top_1w:
        msg_1w = "📅 *TOP 10 ACTIVOS CON RSI MÁS BAJO (Semanal - 1W)* 📅\n\n"
        for i, item in enumerate(top_1w, 1):
            msg_1w += f"*{i}. `{item['ticker']}`*\n   💵 Precio: `${item['price']:,.2f}`\n   📉 RSI: `{item['rsi']:.1f}`\n\n"
        send_telegram_message(msg_1w)

    # 2. Escaneo Diario (1D) RSI
    top_1d = process_timeframe(tickers, '1D', interval='1d', period='60d')
    if top_1d:
        msg_1d = "📉 *TOP 10 ACTIVOS CON RSI MÁS BAJO (Diario - 1D)* 📉\n\n"
        for i, item in enumerate(top_1d, 1):
            msg_1d += f"*{i}. `{item['ticker']}`*\n   💵 Precio: `${item['price']:,.2f}`\n   📉 RSI: `{item['rsi']:.1f}`\n\n"
        send_telegram_message(msg_1d)

    # 3. Escaneo de 1 Hora (1H) RSI
    top_1h = process_timeframe(tickers, '1H', interval='60m', period='30d')
    if top_1h:
        msg_1h = "⏱ *TOP 10 ACTIVOS CON RSI MÁS BAJO (1 Hora - 1H)* ⏱\n\n"
        for i, item in enumerate(top_1h, 1):
            msg_1h += f"*{i}. `{item['ticker']}`*\n   💵 Precio: `${item['price']:,.2f}`\n   📉 RSI: `{item['rsi']:.1f}`\n\n"
        send_telegram_message(msg_1h)

    # 4. Chequear Rupturas de EMA 21 con Volumen (Diario)
    check_ema_breakouts(tickers)

    print("Ciclo completo del bot finalizado.")

if __name__ == "__main__":
    scan_market()
