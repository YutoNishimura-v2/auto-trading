import yfinance as yf
import pandas as pd
from typing import List
from curl_cffi import requests

# Create a session with browser impersonation to bypass Rate Limits
session = requests.Session(impersonate="safari15_5")

def get_nasdaq_100_tickers() -> List[str]:
    """
    Fetches NASDAQ 100 tickers dynamically from Wikipedia.
    Fallback to static list if scraping fails.
    """
    try:
        # Wikipedia URL for NASDAQ 100
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        # Use curl_cffi session to fetch HTML content
        response = session.get(url)
        tables = pd.read_html(response.text)
        # The table with tickers is usually the 5th one (index 4) or check columns
        # Let's try to find the table with 'Ticker' or 'Symbol'
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            elif 'Symbol' in table.columns:
                return table['Symbol'].tolist()
        
        print("Could not find Ticker table on Wikipedia. Using fallback.")
        raise ValueError("Table not found")
        
    except Exception as e:
        print(f"Error fetching dynamic tickers: {e}. Using fallback list.")
        return [
            "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC",
            "QCOM", "TXN", "AVGO", "ADBE", "CSCO", "PEP", "COST", "TMUS", "CMCSA", "AMGN",
            "AMD", "ARM", "MU", "PANW", "CRWD"
        ]

def fetch_stock_data(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical stock data for a given ticker.
    """
    try:
        # Use the custom session
        ticker_obj = yf.Ticker(ticker, session=session)
        df = ticker_obj.history(period=period, interval=interval)
        
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
