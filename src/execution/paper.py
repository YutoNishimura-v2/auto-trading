import json
import os
from datetime import datetime
from typing import Dict, List, Any
from src.config import Config

class PaperTradingEngine:
    def __init__(self, portfolio_file: str = Config.PAPER_TRADING_FILE):
        self.portfolio_file = portfolio_file
        self.portfolio = self._load_portfolio()

    def _load_portfolio(self) -> Dict[str, Any]:
        """Loads portfolio from JSON file."""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Default Initial State
        return {
            "cash": 100000.0, # $100k starting paper cash
            "params": {"initial_cash": 100000.0},
            "positions": {}, # Ticker -> {shares, avg_price, entry_time}
            "trade_history": []
        }

    def _save_portfolio(self):
        """Saves portfolio to JSON file."""
        with open(self.portfolio_file, "w") as f:
            json.dump(self.portfolio, f, indent=4)

    def execute_order(self, ticker: str, action: str, price: float, quantity: int, reason: str = ""):
        """Executes a paper order."""
        timestamp = datetime.now().isoformat()
        
        if action == "BUY":
            cost = price * quantity
            if self.portfolio["cash"] >= cost:
                self.portfolio["cash"] -= cost
                
                # Update positions
                if ticker not in self.portfolio["positions"]:
                    self.portfolio["positions"][ticker] = {"shares": 0, "avg_price": 0.0}
                
                curr_shares = self.portfolio["positions"][ticker]["shares"]
                curr_avg = self.portfolio["positions"][ticker]["avg_price"]
                
                # Calculate new average
                new_shares = curr_shares + quantity
                new_avg = ((curr_shares * curr_avg) + cost) / new_shares
                
                self.portfolio["positions"][ticker] = {
                    "shares": new_shares,
                    "avg_price": new_avg,
                    "last_entry": timestamp
                }
                
                self._log_trade(ticker, "BUY", price, quantity, timestamp, reason)
                self._save_portfolio()
                return True
            else:
                print(f"Insufficient funds to BUY {ticker}")
                return False

        elif action == "SELL":
            if ticker in self.portfolio["positions"] and self.portfolio["positions"][ticker]["shares"] >= quantity:
                revenue = price * quantity
                self.portfolio["cash"] += revenue
                
                self.portfolio["positions"][ticker]["shares"] -= quantity
                if self.portfolio["positions"][ticker]["shares"] == 0:
                    del self.portfolio["positions"][ticker]
                
                self._log_trade(ticker, "SELL", price, quantity, timestamp, reason)
                self._save_portfolio()
                return True
            else:
                print(f"Insufficient shares to SELL {ticker}")
                return False
                
        return False

    def _log_trade(self, ticker, action, price, quantity, timestamp, reason):
        self.portfolio["trade_history"].append({
            "ticker": ticker,
            "action": action,
            "price": price,
            "quantity": quantity,
            "timestamp": timestamp,
            "reason": reason
        })

    def get_portfolio_summary(self):
        return {
            "cash": self.portfolio["cash"],
            "positions": self.portfolio["positions"]
        }
