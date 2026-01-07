import pytest
from unittest.mock import MagicMock
from src.execution.manager import TradeManager

@pytest.fixture
def mock_engine_manager(mocker):
    # Mock the PaperTradingEngine inside TradeManager
    mocker.patch("src.execution.manager.PaperTradingEngine")
    manager = TradeManager()
    manager.engine = MagicMock()
    return manager

def test_buy_signal_strong(mock_engine_manager):
    analysis = {
        "ticker": "NVDA",
        "action": "STRONG_BUY",
        "confidence": 90
    }
    
    mock_engine_manager.process_analysis(analysis, current_price=100.0, atr=5.0)
    
    # Should execute BUY
    # Allocation 5000 / 100 = 50 shares
    mock_engine_manager.engine.execute_order.assert_called_with(
        "NVDA", "BUY", 100.0, 50, reason="Gemini Signal: STRONG_BUY (90%)"
    )

def test_buy_signal_weak_confidence(mock_engine_manager):
    analysis = {
        "ticker": "NVDA",
        "action": "BUY",
        "confidence": 50 # Too low
    }
    
    mock_engine_manager.process_analysis(analysis, current_price=100.0, atr=5.0)
    
    # Should NOT execute trade
    mock_engine_manager.engine.execute_order.assert_not_called()

def test_sell_signal(mock_engine_manager):
    analysis = {
        "ticker": "TSLA",
        "action": "SELL",
        "confidence": 80
    }
    
    # Setup mock portfolio state indicating we own 50 shares
    mock_engine_manager.engine.get_portfolio_summary.return_value = {
        "positions": {
            "TSLA": {"shares": 50}
        }
    }
    
    mock_engine_manager.process_analysis(analysis, current_price=200.0, atr=10.0)
    
    mock_engine_manager.engine.execute_order.assert_called_with(
        "TSLA", "SELL", 200.0, 50, reason="Gemini Signal: SELL"
    )
