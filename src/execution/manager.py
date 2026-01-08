from src.execution.broker_interface import BrokerClient
from src.execution.mock_broker import MockBrokerClient
from src.config import Config
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TradeManager:
    def __init__(self, broker: BrokerClient = None):
        # Default to MockBroker if none provided
        self.broker = broker if broker else MockBrokerClient()

    def get_portfolio(self) -> dict:
        """
        Returns current positions as a dictionary keyed by symbol.
        Format: { "AAPL": { "qty": 10, "avg_entry_price": 150.0, ... }, ... }
        """
        positions_list = self.broker.get_positions()
        return {p["symbol"]: p for p in positions_list}

    def process_analysis(self, analysis_result: dict, current_price: float, atr: float, current_time: datetime = None):
        """
        Decides whether to execute a trade based on Analysis result.
        """
        ticker = analysis_result.get("ticker")
        action = analysis_result.get("action")
        confidence = analysis_result.get("confidence", 0)
        time_horizon = analysis_result.get("time_horizon", "DAY")
        
        # AI Suggestions
        sl_suggestion = analysis_result.get("stop_loss_suggestion", 0.0)
        tp_suggestion = analysis_result.get("take_profit_suggestion", 0.0)
        
        # Fallback if AI returns 0
        if sl_suggestion == 0: sl_suggestion = current_price - (2 * atr)
        if tp_suggestion == 0: tp_suggestion = current_price + (4 * atr)
        
        logger.info(f"Processing Order: {ticker} | Action: {action} | Conf: {confidence}% | Horizon: {time_horizon}")
        
        # 1. Entry Logic
        if action in ["BUY", "STRONG_BUY"]:
            if confidence >= 80:
                # Risk Management: Use 2% of Equity per trade
                account = self.broker.get_account()
                equity = account.get("equity", 100000.0)
                buying_power = account.get("buying_power", 0.0)
                
                risk_per_trade = equity * 0.02 # 2% risk
                stop_distance = abs(current_price - sl_suggestion)
                if stop_distance == 0: stop_distance = current_price * 0.05
                
                shares_based_on_risk = risk_per_trade / stop_distance
                max_shares_bp = buying_power / current_price
                shares = math.floor(min(shares_based_on_risk, max_shares_bp))
                
                if shares > 0:
                    logger.info(f"Attempting to BUY {shares} shares of {ticker} (TP: {tp_suggestion}, SL: {sl_suggestion})...")
                    try:
                        order = self.broker.submit_order(
                            ticker, shares, "buy", 
                            stop_loss=sl_suggestion, 
                            take_profit=tp_suggestion,
                            time_horizon=time_horizon,
                            timestamp=current_time
                        )
                        if order.get("status") == "filled":
                            logger.info(f"Successfully Bought {ticker}")
                            # Add reason for Tape
                            order["reason"] = f"Entry ({time_horizon})"
                            return ("TRADE_ALERT", order)
                    except Exception as e:
                        logger.error(f"Order Failed: {e}")
                else:
                    logger.warning(f"Calculated 0 shares for {ticker}")

            else:
                logger.info(f"Confidence too low ({confidence}%) for {ticker}")

        # 2. Exit Logic (Check existing positions)
        elif action == "SELL":
            # Check if we own it
            positions = self.broker.get_positions()
            pos = next((p for p in positions if p["symbol"] == ticker), None)
            
            if pos:
                shares_owned = pos["qty"]
                logger.info(f"Attempting to SELL {shares_owned} shares of {ticker}...")
                try:
                    order = self.broker.submit_order(ticker, shares_owned, "sell")
                    if order.get("status") == "filled":
                        logger.info(f"Successfully Sold {ticker}")
                except Exception as e:
                    logger.error(f"Order Failed: {e}")

    def start_monitoring_loop(self, provider, max_iterations: int = 5):
        """
        Real-time monitoring loop.
        Polls prices, checks triggers, and yields status updates.
        """
        # Update Broker's price fetching mechanism or pass prices explicitly
        # For MockBroker, we need to inject the current prices
        
        for i in range(max_iterations):
            current_time = provider.get_time()
            logger.info(f"Monitoring Cycle {i+1}/{max_iterations} at {current_time}...")
            
            # 1. Update Prices in Broker (for P&L)
            # We need to fetch prices for all held positions
            positions = self.broker.get_positions()
            market_data = {}
            for pos in positions:
                ticker = pos['symbol']
                price = provider.get_current_price(ticker)
                market_data[ticker] = price
                
                # Hack: Update the position's current price in MockBroker directly 
                # (since MockBroker usually fetches itself)
                # Ideally, Broker should accept a provider, but for now we pass data
                if hasattr(self.broker, 'update_prices'):
                    self.broker.update_prices(market_data)

            # 2. Check Triggers (TP/SL)
            # We need to pass the provider or prices to check_triggers?
            # MockBroker.check_triggers currently calls fetch_current_price internally.
            # We should modify MockBroker to accept prices or override fetch_current_price.
            # EASIER: Let's pass the prices to check_triggers if possible, or patch it.
            # For this iteration, let's assume MockBroker needs to be updated to use the provider 
            # OR we pass the provider to the broker.
            
            # Let's pass the provider to check_triggers if we modify Broker, 
            # OR we just pass the market_data to check_triggers.
            
            # Let's modify check_triggers in Broker to accept market_data (optional)
            triggered = self.broker.check_triggers(market_data=market_data)
            
            for order in triggered:
                yield ("TRADE_ALERT", order)
                
            # 3. Yield Portfolio Update
            account = self.broker.get_account()
            yield ("PORTFOLIO_UPDATE", account)
            
            # Advance Time
            provider.tick()
            
            # Yield Monitor Event for UI Updates (Clock, etc)
            yield ("MONITOR", {"time": provider.get_time()})


    def perform_eod_review(self, analyst):
        """
        Iterates through all open positions and asks Gemini to re-evaluate them.
        Yields status updates and trade alerts.
        """
        positions = self.broker.get_positions()
        if not positions:
            return

        from src.data.loader import fetch_stock_data
        from src.analysis.chart import generate_chart_image
        from src.screening.indicators import calculate_technical_indicators

        for pos in positions:
            ticker = pos["symbol"]
            qty = pos["qty"]
            entry = pos["avg_entry_price"]
            current = pos["current_price"]
            
            yield ("STATUS", f"⚖️ EOD Review: Re-evaluating {ticker}...")
            
            # Generate fresh chart
            df = fetch_stock_data(ticker)
            if not df.empty:
                df = calculate_technical_indicators(df)
                chart_bytes = generate_chart_image(df, ticker)
                
                # Ask Gemini
                decision = analyst.reevaluate_position(ticker, entry, current, chart_bytes)
                
                yield ("EOD_DECISION", decision)
                
                if decision["action"] == "CLOSE_NOW":
                    logger.info(f"EOD Decision: Closing {ticker}")
                    try:
                        order = self.broker.submit_order(ticker, qty, "sell")
                        order["reason"] = f"EOD Review: {decision['reasoning']}"
                        yield ("TRADE_ALERT", order)
                    except Exception as e:
                        logger.error(f"Failed to close {ticker}: {e}")
                else:
                    logger.info(f"EOD Decision: Holding {ticker}")

    def liquidate_all(self):
        """Liquidates all positions (Day Trade End)."""
        logger.info("Executing End-of-Day Liquidation...")
        self.broker.close_all_positions()
