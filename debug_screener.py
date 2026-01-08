import pandas as pd
import os
import traceback

cache_file = "data/cache/sim_screening_2026-01-07.csv"

print(f"Checking cache file: {cache_file}")
if not os.path.exists(cache_file):
    print("Cache file not found!")
    exit()

try:
    # Replicate MarketProvider loading logic
    print("Loading CSV...")
    df = pd.read_csv(cache_file, index_col=0, parse_dates=True, header=[0, 1])
    
    print(f"Raw Shape: {df.shape}")
    
    # Replicate cleaning logic
    if not df.empty:
        first_idx = df.index[0]
        if str(first_idx) == 'Date' or pd.isna(first_idx):
            print("Dropping first row (Date label)...")
            df = df.iloc[1:]
    
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df[df.index.notna()]
    
    print(f"Cleaned Shape: {df.shape}")

    # Replicate Screener extraction logic
    tickers = df.columns.get_level_values(1).unique()
    print(f"Found {len(tickers)} tickers.")
    
    sample_ticker = tickers[0]
    print(f"\nTesting extraction for {sample_ticker}...")
    
    try:
        ticker_df = df.xs(sample_ticker, axis=1, level=1, drop_level=True)
        print(f"Extracted Shape: {ticker_df.shape}")
        
        # Check length
        if len(ticker_df) < 20:
            print("FAIL: Not enough data (<20)")
        else:
            print("PASS: Length OK")
            
        # Test Indicators
        from src.screening.indicators import calculate_technical_indicators
        from src.config import Config
        
        print("\nCalculating Indicators...")
        df_ind = calculate_technical_indicators(ticker_df)
        last_row = df_ind.iloc[-1]
        prev_row = df_ind.iloc[-2]
        
        print("Last Row Indicators:")
        print(last_row[['Close', 'Volume', 'VOL_SMA_20', 'ATR']])
        
        # Check Liquidity
        min_vol = Config.MIN_VOLUME
        print(f"\nLiquidity Check: Volume SMA {last_row['VOL_SMA_20']} >= {min_vol}?")
        if last_row['VOL_SMA_20'] < min_vol:
            print("FAIL: Liquidity")
        else:
            print("PASS: Liquidity")
            
        # Check Rel Vol
        rel_vol = last_row['Volume'] / last_row['VOL_SMA_20'] if last_row['VOL_SMA_20'] > 0 else 0
        print(f"Rel Vol: {rel_vol}")
        
        # Check Gap
        gap_percent = ((last_row['Open'] - prev_row['Close']) / prev_row['Close']) * 100
        print(f"Gap %: {gap_percent}")

    except Exception as e:
        print(f"Extraction/Indicator Failed: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"Global Error: {e}")
    traceback.print_exc()
