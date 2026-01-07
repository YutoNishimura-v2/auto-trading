import yfinance as yf
import pandas as pd
from typing import List

def get_nasdaq_100_tickers() -> List[str]:
    """
    Fetches NASDAQ 100 tickers.
    For MVP, returns a static list of top tech stocks to ensure reliability.
    """
    # In a real app, scrape Wikipedia or use an API.
    # For MVP/Safety, using a predefined top list.
    return [
        "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC",
        "QCOM", "TXN", "AVGO", "ADBE", "CSCO", "PEP", "COST", "TMUS", "CMCSA", "AMGN"
    ]

def fetch_stock_data(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical stock data for a given ticker.
    """
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, multi_level_index=False)
        if df.empty:
            print(f"Warning: No data found for {ticker}")
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def fetch_current_price(ticker: str) -> float:
    """Fetches the current real-time price."""
    try:
        ticker_obj = yf.Ticker(ticker)
        # Try different keys as yfinance API can be inconsistent
        price = ticker_obj.info.get('regularMarketPrice') or \
                ticker_obj.info.get('currentPrice') or \
                ticker_obj.fast_info.last_price
        return float(price)
    except Exception:
        return 0.0
