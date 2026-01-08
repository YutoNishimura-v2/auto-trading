import pandas as pd
from src.data.loader import fetch_stock_data, get_nasdaq_100_tickers
from src.screening.indicators import calculate_technical_indicators
from src.config import Config

def screen_stocks(whitelist: list = None, provider=None) -> pd.DataFrame:
    """
    Screens stocks for Day Trading opportunities.
    """
    if whitelist:
        tickers = whitelist
    else:
        tickers = get_nasdaq_100_tickers()
    screened_list = []

    print(f"Screening {len(tickers)} tickers for Day Trading setups...")
    
    if not provider:
        print("ERROR: No MarketProvider passed to screener.")
        return pd.DataFrame()

    for ticker in tickers:
        try:
            # UNIFIED LOGIC: Ask provider for history
            # The provider handles whether it's from API (Real-time) or Cache (Simulation)
            df = provider.get_history(ticker, period="6mo")
            
            if df.empty or len(df) < 50:
                print(f"Debug {ticker}: Data length {len(df)} < 50. Skipping.")
                continue
            
            # Basic Indicators
            df = calculate_technical_indicators(df)
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # 1. Liquidity & Price Check
            if last_row['VOL_SMA_20'] < Config.MIN_VOLUME:
                print(f"Debug {ticker}: Failed Liquidity ({last_row['VOL_SMA_20']} < {Config.MIN_VOLUME})")
                continue
            
            if last_row['Close'] < Config.MIN_PRICE:
                print(f"Debug {ticker}: Failed Price ({last_row['Close']} < {Config.MIN_PRICE})")
                continue
                
            # 2. Relative Volume (Current Volume vs 20-day Avg)
            # Note: If running mid-day, volume might be lower than full day avg.
            # But for "Gap" trading, high volume at open is key.
            # Let's use a lower threshold if running early, or just check if it's significant.
            rel_vol = last_row['Volume'] / last_row['VOL_SMA_20'] if last_row['VOL_SMA_20'] > 0 else 0
            
            # 3. Gap %
            # Open today vs Close yesterday
            gap_percent = ((last_row['Open'] - prev_row['Close']) / prev_row['Close']) * 100
            
            print(f"Debug {ticker}: PASSED. RelVol={rel_vol:.2f}, Gap={gap_percent:.2f}%")
            
            # 4. Volatility (ATR %)
            atr_percent = (last_row['ATR'] / last_row['Close']) * 100
            
            # Filter Logic for Day Trading Candidates
            # We want things moving TODAY.
            # Criteria: RelVol > 1.0 (at least avg volume pace), Gap > 1% (or < -1%)
            
            if abs(gap_percent) > 1.0 or rel_vol > 1.5:
                screened_list.append({
                    'Ticker': ticker,
                    'Price': last_row['Close'],
                    'Gap%': gap_percent,
                    'RelVol': rel_vol,
                    'ATR': last_row['ATR'],
                    'ATR%': atr_percent,
                    'RSI': last_row['RSI'],
                    'Volume': last_row['Volume']
                })
                
        except Exception as e:
            print(f"Error screening {ticker}: {e}")
            continue
    
    results = pd.DataFrame(screened_list)
    
    if not results.empty:
        # Sort by Absolute Gap % to find biggest movers
        results['AbsGap'] = results['Gap%'].abs()
        results = results.sort_values(by='AbsGap', ascending=False)
        
        # Return Top 5
        return results.head(5)
        
    return results

if __name__ == "__main__":
    results = screen_stocks()
    print("\nTop Day Trading Candidates:")
    print(results[['Ticker', 'Price', 'Gap%', 'RelVol', 'ATR%']])
