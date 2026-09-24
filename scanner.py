def calculate_rsi(df, window=14):
    """Calcula el RSI usando el método de Wilder (igual que TradingView)."""
    delta = df['Close'].diff()
    
    # Separar ganancias y pérdidas
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Usar EWM con alpha = 1/window (Método Wilder / RMA utilizado por TradingView)
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df
