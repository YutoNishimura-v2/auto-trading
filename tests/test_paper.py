import pytest
import os
import json
from src.execution.paper import PaperTradingEngine

TEST_PORTFOLIO_FILE = "test_portfolio.json"

@pytest.fixture
def paper_engine():
    # Setup
    if os.path.exists(TEST_PORTFOLIO_FILE):
        os.remove(TEST_PORTFOLIO_FILE)
    
    engine = PaperTradingEngine(portfolio_file=TEST_PORTFOLIO_FILE)
    yield engine
    
    # Teardown
    if os.path.exists(TEST_PORTFOLIO_FILE):
        os.remove(TEST_PORTFOLIO_FILE)

def test_initial_state(paper_engine):
    summary = paper_engine.get_portfolio_summary()
    assert summary['cash'] == 100000.0
    assert summary['positions'] == {}

def test_buy_order(paper_engine):
    # Buy 10 shares at $100
    success = paper_engine.execute_order("AAPL", "BUY", 100.0, 10)
    
    assert success is True
    summary = paper_engine.get_portfolio_summary()
    assert summary['cash'] == 100000.0 - 1000.0
    assert summary['positions']['AAPL']['shares'] == 10
    assert summary['positions']['AAPL']['avg_price'] == 100.0

def test_buy_insufficient_funds(paper_engine):
    # Try to buy more than cash
    success = paper_engine.execute_order("BRK-A", "BUY", 200000.0, 1)
    assert success is False
    assert paper_engine.get_portfolio_summary()['cash'] == 100000.0

def test_sell_order(paper_engine):
    # First buy
    paper_engine.execute_order("AAPL", "BUY", 100.0, 10)
    
    # Then sell 5
    success = paper_engine.execute_order("AAPL", "SELL", 110.0, 5)
    
    assert success is True
    summary = paper_engine.get_portfolio_summary()
    
    # Cash = 99000 (after buy) + 550 (sell) = 99550
    assert summary['cash'] == 99550.0
    assert summary['positions']['AAPL']['shares'] == 5

def test_sell_not_owned(paper_engine):
    success = paper_engine.execute_order("MSFT", "SELL", 100.0, 1)
    assert success is False
