from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import time
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
from src.data.loader import fetch_current_price, fetch_stock_data

class MarketDataProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        """Returns the current price (Real-time or Simulated)."""
        pass

    @abstractmethod
    def get_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        """Returns historical OHLCV data ending at the current (simulated) time."""
        pass

    @abstractmethod
    def tick(self):
        """Advances time (for simulation). No-op for real-time."""
        pass
    
    @abstractmethod
    def get_time(self) -> datetime:
        """Returns the current system time (Real-time or Simulated)."""
        pass

class RealTimeProvider(MarketDataProvider):
    def get_current_price(self, ticker: str) -> float:
        return fetch_current_price(ticker)

    def get_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        # Real-time: just fetch from API
        return fetch_stock_data(ticker, period=period)

    def tick(self):
        time.sleep(2) # Wait 2 seconds in real-time loop

    def get_time(self) -> datetime:
        return datetime.now()

class HistoricalReplayProvider(MarketDataProvider):
    def __init__(self, tickers: List[str], date: datetime):
        self.tickers = tickers
        self.date = date
        self.data_cache = {}
        self.current_index = 0
        self.max_index = 0
        self.timestamps = []
        
        print(f"Loading historical data for {date.date()}...")
        self._load_data()
        self._load_screening_data()

    def _load_screening_data(self):
        """Loads or downloads daily data for screening (Gap%, Vol SMA)."""
        import os
        cache_dir = "data/cache"
        date_str = self.date.strftime('%Y-%m-%d')
        cache_file = f"{cache_dir}/sim_screening_{date_str}.csv"
        
        # 1. Try Loading from Cache
        if os.path.exists(cache_file):
            print(f"Loading screening data from cache: {cache_file}")
            try:
                # Read with header=[0, 1] to capture Price and Ticker levels
                self.screening_cache = pd.read_csv(cache_file, index_col=0, parse_dates=True, header=[0, 1])
                
                # Clean invalid rows
                if not self.screening_cache.empty:
                     first_idx = self.screening_cache.index[0]
                     if str(first_idx) == 'Date' or pd.isna(first_idx):
                         self.screening_cache = self.screening_cache.iloc[1:]
                
                self.screening_cache.index = pd.to_datetime(self.screening_cache.index, errors='coerce')
                self.screening_cache = self.screening_cache[self.screening_cache.index.notna()]

                print("Loaded cached screening data.")
                return
            except Exception as e:
                print(f"Error reading screening cache: {e}. Re-downloading...")

        # 2. Download from API
        # Fetch ~180 days to match real-time "6mo" and ensure >50 rows
        start_date = pd.Timestamp(self.date) - pd.Timedelta(days=180)
        end_date = pd.Timestamp(self.date) + pd.Timedelta(days=1) 
        
        tickers_str = " ".join(self.tickers)
        print(f"Downloading daily history for screening ({start_date.date()} to {end_date.date()})...")
        
        try:
            from src.data.loader import session
            # Download daily data
            df = yf.download(tickers_str, start=start_date, end=end_date, interval="1d", progress=False, session=session)
            
            if df.empty:
                print("Warning: No screening data found.")
                self.screening_cache = pd.DataFrame()
                return

            # Save to cache
            os.makedirs(cache_dir, exist_ok=True)
            df.to_csv(cache_file)
            print(f"Saved screening data to cache: {cache_file}")
            self.screening_cache = df
            
        except Exception as e:
            print(f"Error downloading screening data: {e}")
            self.screening_cache = pd.DataFrame()

    def _load_data(self):
        """Loads 1-minute intraday data for the simulation date."""
        import os
        cache_dir = "data/cache"
        date_str = self.date.strftime('%Y-%m-%d')
        cache_file = f"{cache_dir}/sim_data_{date_str}.csv"
        
        # 1. Try Loading from Cache
        if os.path.exists(cache_file):
            print(f"Loading data from cache: {cache_file}")
            try:
                self.data_cache = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                # Forward Fill to handle missing minutes
                self.data_cache = self.data_cache.ffill().bfill()
                # Drop columns that are still all NaNs
                self.data_cache.dropna(axis=1, how='all', inplace=True)
                
                self.timestamps = self.data_cache.index.unique().sort_values()
                
                # Fast-forward to Market Open (09:30)
                # Assuming timestamps are datetime objects (localized or naive?)
                # If they are naive, we assume market time.
                # We need to find the first timestamp >= 09:30
                market_open_time = self.date.replace(hour=9, minute=30, second=0, microsecond=0)
                
                # Find index
                future_times = [i for i, t in enumerate(self.timestamps) if t >= market_open_time]
                if future_times:
                    self.current_index = future_times[0]
                    print(f"Simulation fast-forwarded to Market Open: {self.timestamps[self.current_index]}")
                else:
                    self.current_index = 0
                    
                self.max_index = len(self.timestamps) - 1
                print(f"Loaded {len(self.timestamps)} minutes of cached data.")
                return
            except Exception as e:
                print(f"Error reading cache: {e}. Re-downloading...")

        # 2. Download from API (Fallback)
        print(f"Downloading 1m data for {self.date.date()}...")
        try:
            from src.data.loader import session
            # Note: yfinance download for 1d with 1m interval is tricky if not "today"
            # But for simulation we assume we might be running on a past date.
            # yfinance only supports 7 days of 1m data. 
            # If date is older than 7 days, this will fail or return empty.
            # For now, assuming recent date or user has data.
            
            # To handle rate limits, we download in bulk if possible, but 1m data 
            # for many tickers is heavy. Let's do it per ticker or small batches if needed.
            # Actually, yf.download can handle multiple tickers.
            
            tickers_str = " ".join(self.tickers)
            # Fetch 1 day of data
            start_date = self.date
            end_date = self.date + timedelta(days=1)
            
            df = yf.download(tickers_str, start=start_date, end=end_date, interval="1m", progress=False, session=session)
            
            if df.empty:
                print("Warning: No data found for date.")
                return

            # Process MultiIndex columns if multiple tickers
            # yfinance returns (Price, Ticker) columns
            # We want a flattened structure or just keep it as is?
            # Existing logic expects: Index=Time, Columns=Tickers (Close price)
            # But we need OHLC for full simulation? 
            # For now, let's just cache the 'Close' price for the simple simulation loop.
            
            if isinstance(df.columns, pd.MultiIndex):
                # Extract Close prices
                close_df = df.xs('Close', axis=1, level=0)
            else:
                # Single ticker
                close_df = df['Close'].to_frame(name=self.tickers[0])

            # Save to cache
            os.makedirs(cache_dir, exist_ok=True)
            close_df.to_csv(cache_file)
            print(f"Saved data to cache: {cache_file}")
            
            self.data_cache = close_df
            # Forward Fill to handle missing minutes
            self.data_cache = self.data_cache.ffill().bfill()
            # Drop columns that are still all NaNs
            self.data_cache.dropna(axis=1, how='all', inplace=True)
            
            self.timestamps = self.data_cache.index.unique().sort_values()
            self.max_index = len(self.timestamps) - 1
            
        except Exception as e:
            print(f"Error downloading data: {e}")

    def get_current_price(self, ticker: str) -> float:
        if self.data_cache is None or self.data_cache.empty:
            return 0.0
            
        # Get price at current timestamp
        try:
            # If simulation has gone past the data (e.g. Market Closed), return the LAST price
            if self.current_index > self.max_index:
                if ticker in self.data_cache.columns:
                    last_price = self.data_cache.iloc[self.max_index][ticker]
                    return float(last_price) if not pd.isna(last_price) else 0.0
                return 0.0

            current_time = self.timestamps[self.current_index]
            price = self.data_cache.loc[current_time, ticker]
            
            # Handle NaN (missing data for this minute)
            if pd.isna(price):
                # Forward fill from previous valid price if possible
                # For now, try to find the last valid price in the cache up to this point
                # This is expensive to do every tick if we search back.
                # Better to rely on the fact that we forward-filled in _load_data?
                # We didn't ffill in _load_data for the unified provider yet.
                # Let's just return the last known valid price if current is NaN
                if self.current_index > 0:
                     prev_time = self.timestamps[self.current_index - 1]
                     prev_price = self.data_cache.loc[prev_time, ticker]
                     if not pd.isna(prev_price):
                         return float(prev_price)
                return 0.0 
                
            return float(price)
        except IndexError:
            # End of data, return last known?
            if ticker in self.data_cache.columns:
                 return float(self.data_cache.iloc[-1][ticker])
            return 0.0
        except KeyError:
            return 0.0

    def get_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        """
        Returns historical daily data for the ticker, up to the simulation date.
        Uses the screening_cache which contains daily OHLCV.
        """
        if not hasattr(self, 'screening_cache') or self.screening_cache.empty:
            print(f"Warning: No screening cache available for {ticker}")
            return pd.DataFrame()

        try:
            # Check if ticker is in cache
            if isinstance(self.screening_cache.columns, pd.MultiIndex):
                if ticker not in self.screening_cache.columns.get_level_values(1):
                    return pd.DataFrame()
                
                # Extract ticker data
                df = self.screening_cache.xs(ticker, axis=1, level=1, drop_level=True)
            else:
                return pd.DataFrame()

            # Filter data up to simulation date (inclusive)
            # The cache might contain data AFTER the sim date if we downloaded a range that includes it.
            # We must strictly cut off future data to prevent look-ahead bias.
            mask = df.index <= self.date
            df_filtered = df.loc[mask]
            
            return df_filtered
            
        except Exception as e:
            print(f"Error extracting history for {ticker}: {e}")
            return pd.DataFrame()

    def tick(self):
        if self.current_index < self.max_index:
            self.current_index += 1
        
        # Simulate time passing
        time.sleep(0.05) # Fast replay

    def get_time(self) -> datetime:
        if self.timestamps is not None and len(self.timestamps) > 0:
            return self.timestamps[self.current_index]
        return self.date
