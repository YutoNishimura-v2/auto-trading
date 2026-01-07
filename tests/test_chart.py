import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.analysis.chart import generate_chart_image

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Open": [100, 101, 102],
        "High": [105, 106, 107],
        "Low": [95, 96, 97],
        "Close": [102, 103, 104],
        "Volume": [1000, 1000, 1000],
        "SMA_50": [90, 91, 92],
        "SMA_200": [80, 81, 82],
        "BBL_20_2.0": [90, 90, 90],
        "BBU_20_2.0": [110, 110, 110]
    }, index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]))

@patch("src.analysis.chart.mpf.plot")
def test_generate_chart_calls_mpf(mock_plot, sample_df):
    
    result = generate_chart_image(sample_df, "TEST")
    
    assert mock_plot.called
    assert isinstance(result, bytes)
    
    # Check args
    args, kwargs = mock_plot.call_args
    assert kwargs['type'] == 'candle'
    assert kwargs['volume'] is True
    assert 'addplot' in kwargs

def test_generate_chart_empty_df():
    result = generate_chart_image(pd.DataFrame(), "TEST")
    assert result == b""
