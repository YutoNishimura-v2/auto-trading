from src.execution.paper import PaperTradingEngine
from src.config import Config
import math

class TradeManager:
    def __init__(self):
        self.engine = PaperTradingEngine()

    def process_analysis(self, analysis_result: dict, current_price: float, atr: float):
        """
        Decides whether to execute a trade based on Analysis result.
        """
        ticker = analysis_result.get("ticker")
        action = analysis_result.get("action")
        confidence = analysis_result.get("confidence", 0)
        
        print(f"Processing Order: {ticker} | Action: {action} | Conf: {confidence}%")
        
        # 1. Entry Logic
        if action in ["BUY", "STRONG_BUY"]:
            if confidence >= 80:
                # Calculate Position Size (e.g., 2% risk rule or fixed amount)
                # For MVP, let's use fixed $5000 allocation per trade
                allocation = 5000.0
                shares = math.floor(allocation / current_price)
                
                if shares > 0:
                    print(f"Attempting to BUY {shares} shares of {ticker}...")
                    success = self.engine.execute_order(
                        ticker, "BUY", current_price, shares, 
                        reason=f"Gemini Signal: {action} ({confidence}%)"
                    )
                    if success:
                        print(f"Successfully Bought {ticker}")
            else:
                print(f"Confidence too low ({confidence}%) for {ticker}")

        # 2. Exit Logic (Check existing positions)
        # Note: In a real system, we would loop through portfolio positions and check stops.
        # Here, we only check if the Analysis said SELL for this specific ticker.
        elif action == "SELL":
            # Check if we own it
            positions = self.engine.get_portfolio_summary()["positions"]
            if ticker in positions:
                shares_owned = positions[ticker]["shares"]
                print(f"Attempting to SELL {shares_owned} shares of {ticker}...")
                success = self.engine.execute_order(
                    ticker, "SELL", current_price, shares_owned,
                    reason=f"Gemini Signal: {action}"
                )
                if success:
                    print(f"Successfully Sold {ticker}")
