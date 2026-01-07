import pytest
import pandas as pd
import numpy as np
from src.screening.indicators import calculate_technical_indicators

@pytest.fixture
def sample_data():
    """Generates a sample DataFrame for testing indicators."""
    dates = pd.date_range(start="2023-01-01", periods=300, freq="D")
    df = pd.DataFrame(index=dates)
    # Create a simple trend
    df['Close'] = np.linspace(100, 200, 300)
    df['Open'] = df['Close']
    df['High'] = df['Close'] + 1
    df['Low'] = df['Close'] - 1
    df['Volume'] = 1000000
    return df

def test_calculate_technical_indicators_structure(sample_data):
    df = calculate_technical_indicators(sample_data.copy())
    
    # Check if columns are added
    expected_cols = ['ATR', 'RSI', 'SMA_50', 'SMA_200', 'VOL_SMA_20']
    for col in expected_cols:
        assert col in df.columns

def test_indicators_logic(sample_data):
    df = calculate_technical_indicators(sample_data.copy())
    
    # SMA 50 should be lower than Price in an uptrend (lagging)
    assert df['SMA_50'].iloc[-1] < df['Close'].iloc[-1]
    
    # RSI should be calculable (not all NaN)
    assert not df['RSI'].isna().all()

def test_empty_dataframe():
    df = pd.DataFrame()
    result = calculate_technical_indicators(df)
    assert result.empty
