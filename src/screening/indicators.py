import pandas as pd
import pandas_ta as ta

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators for a given DataFrame.
    
    Args:
        df: DataFrame with 'Open', 'High', 'Low', 'Close', 'Volume' columns.
        
    Returns:
        DataFrame with added indicator columns.
    """
    if df.empty:
        return df
    
    # Ensure index is datetime
    # if not isinstance(df.index, pd.DatetimeIndex):
    #     df.index = pd.to_datetime(df.index)

    # 1. ATR (Volatility)
    df['ATR'] = df.ta.atr(length=14)
    
    # 2. RSI (Momentum)
    df['RSI'] = df.ta.rsi(length=14)
    
    # 3. Moving Averages (Trend)
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_200'] = ta.sma(df['Close'], length=200)
    
    # 4. Bollinger Bands (Volatility/Mean Reversion)
    bb = ta.bbands(df['Close'], length=20)
    if bb is not None:
        df = pd.concat([df, bb], axis=1)
        
    # 5. Volume Moving Average (Liquidity)
    df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()

    return df
