import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp") # Using a newer model if available, or fallback to pro

    # Trading Parameters
    INITIAL_CAPITAL = 100000.0
    POSITION_SIZE_PCT = 0.05  # 5% of equity per trade
    MAX_POSITIONS = 5
    
    # Screening Criteria
    MIN_VOLUME = 2000000  # Increased to 2M to filter low liquidity
    MIN_PRICE = 5.0       # Minimum price to avoid penny stocks
    MIN_ATR = 1.0        # Minimum ATR (kept from original)
    TICKER_LIMIT = 20 # Max number of tickers to screen (kept from original)
    
    # Risk Management
    DEFAULT_STOP_LOSS_PCT = 0.02
    DEFAULT_TAKE_PROFIT_PCT = 0.04  
    
    # Paper Trading
    PAPER_TRADING_FILE = "paper_portfolio.json"

    # Simulation Mode
    IS_SIMULATION = True
