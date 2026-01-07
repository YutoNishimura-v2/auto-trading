import pandas as pd
from src.data.loader import fetch_stock_data, get_nasdaq_100_tickers
from src.screening.indicators import calculate_technical_indicators
from src.config import Config

def screen_stocks() -> pd.DataFrame:
    """
    Screens filters stocks based on liquidity, volatility, and momentum.
    Returns a DataFrame of qualifying stocks with their latest metrics.
    """
    tickers = get_nasdaq_100_tickers()[:Config.TICKER_LIMIT]
    screened_list = []

    print(f"Screening {len(tickers)} tickers...")

    for ticker in tickers:
        df = fetch_stock_data(ticker)
        if df.empty or len(df) < 50: # Minimum data requirement
            continue
            
        df = calculate_technical_indicators(df)
        last_row = df.iloc[-1]
        
        # 1. Liquidity Check
        if last_row['VOL_SMA_20'] < Config.MIN_VOLUME:
            continue
            
        # 2. Volatility Check (High ATR means tradeable swings)
        # Normalizing ATR by price for comparison (ATR %)
        last_price = last_row['Close']
        if last_price == 0: continue
        
        if last_row['ATR'] < Config.MIN_ATR:
            continue
            
        atr_percent = (last_row['ATR'] / last_price) * 100
        
        # 3. Momentum Logic (Example: RSI not extremely overbought, but strong)
        # For this logic, we just want to see everything for now, but sort by Momentum
        
        screened_list.append({
            'Ticker': ticker,
            'Price': last_price,
            'RSI': last_row['RSI'],
            'ATR': last_row['ATR'],
            'ATR%': atr_percent,
            'Volume': last_row['Volume']
        })
    
    results = pd.DataFrame(screened_list)
    
    if not results.empty:
        # Sort by ATR% (Volatility) to find "movers"
        results = results.sort_values(by='ATR%', ascending=False)
        
    return results

if __name__ == "__main__":
    results = screen_stocks()
    print("\nScreening Results:")
    print(results.head(10))
