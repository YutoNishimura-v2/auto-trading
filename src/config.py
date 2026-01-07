import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp") # Using a newer model if available, or fallback to pro

    # Trading Universe
    TICKER_LIMIT = 20 # Max number of tickers to screen

    # Screening Parameters
    MIN_VOLUME = 1000000 # Minimum daily volume
    MIN_ATR = 1.0        # Minimum ATR

    # Paper Trading
    PAPER_TRADING_FILE = "paper_portfolio.json"

    # Simulation Mode
    IS_SIMULATION = True
