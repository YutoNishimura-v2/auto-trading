import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.screening.screener import screen_stocks
from src.config import Config

@patch("src.screening.screener.get_nasdaq_100_tickers")
@patch("src.screening.screener.fetch_stock_data")
def test_screen_stocks_filtering(mock_fetch, mock_get_tickers):
    # Setup
    mock_get_tickers.return_value = ["GOOD", "BAD_VOL", "BAD_ATR"]
    
    # Mock Data Responses
    def get_data(ticker, **kwargs):
        df = pd.DataFrame(index=pd.date_range("2023-01-01", periods=100))
        df['Close'] = 100.0
        df['Open'] = 100.0
        df['High'] = 105.0
        df['Low'] = 95.0
        df['Volume'] = 5000000 # Good volume by default
        
        if ticker == "BAD_VOL":
            df['Volume'] = 100 # Low volume
        elif ticker == "BAD_ATR":
            # Very stable, low ATR
            df['High'] = 100.1
            df['Low'] = 99.9
            
        return df

    mock_fetch.side_effect = get_data
    
    # Run
    results = screen_stocks()
    
    # Verify
    assert not results.empty
    # "GOOD" should be in results
    assert "GOOD" in results['Ticker'].values
    # "BAD_VOL" should be filtered out
    assert "BAD_VOL" not in results['Ticker'].values
    # "BAD_ATR" might be filtered out depending on config defaults (MIN_ATR=1.0)
    # With price 100, ATR needs to be > 1.0. Our BAD_ATR has tiny range.
    assert "BAD_ATR" not in results['Ticker'].values

def test_screen_stocks_no_data(mocker):
    mocker.patch("src.screening.screener.get_nasdaq_100_tickers", return_value=["TEST"])
    mocker.patch("src.screening.screener.fetch_stock_data", return_value=pd.DataFrame())
    
    results = screen_stocks()
    assert results.empty
