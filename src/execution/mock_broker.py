import json
import os
from datetime import datetime
from typing import Dict, List, Any
from src.execution.broker_interface import BrokerClient
from src.config import Config
from src.data.loader import fetch_current_price

class MockBrokerClient(BrokerClient):
    """
    Mock Broker implementation for Paper Trading.
    Simulates:
    - Instant fills at current market price.
    - 4x Day Trading Buying Power.
    - Commission-free trading.
    - Persistence via JSON file.
    """
    
    def __init__(self, portfolio_file: str = Config.PAPER_TRADING_FILE):
        self.portfolio_file = portfolio_file
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Initial State
        return {
            "cash": 100000.0,
            "equity": 100000.0,
            "positions": {}, # symbol -> {qty, avg_entry_price}
            "orders": []
        }

    def _save_state(self):
        with open(self.portfolio_file, "w") as f:
            json.dump(self.state, f, indent=4)

    def _update_equity(self):
        """Recalculates equity based on current market prices."""
        positions_value = 0.0
        for symbol, pos in self.state["positions"].items():
            current_price = fetch_current_price(symbol)
            positions_value += pos["qty"] * current_price
        
        self.state["equity"] = self.state["cash"] + positions_value

    def get_account(self) -> Dict[str, Any]:
        self._update_equity()
        equity = self.state["equity"]
        
        # Day Trading Buying Power is typically 4x Equity for intraday
        # But limited by cash for opening new positions if we don't want to go negative cash (margin loan)
        # For simplicity, we'll model Buying Power as 4 * Equity, allowing cash to go negative (margin used).
        buying_power = equity * 4.0
        
        return {
            "cash": self.state["cash"],
            "portfolio_value": equity,
            "equity": equity,
            "buying_power": buying_power,
            "status": "ACTIVE"
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        positions_list = []
        for symbol, pos in self.state["positions"].items():
            current_price = fetch_current_price(symbol)
            market_value = pos["qty"] * current_price
            cost_basis = pos["qty"] * pos["avg_entry_price"]
            unrealized_pl = market_value - cost_basis
            unrealized_plpc = (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0.0
            
            positions_list.append({
                "symbol": symbol,
                "qty": pos["qty"],
                "avg_entry_price": pos["avg_entry_price"],
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pl": unrealized_pl,
                "unrealized_plpc": unrealized_plpc,
                "tp": pos.get("take_profit"),
                "sl": pos.get("stop_loss")
            })
        return positions_list

    def submit_order(self, symbol: str, qty: int, side: str, type: str = "market", time_in_force: str = "day",
                     stop_loss: float = None, take_profit: float = None, time_horizon: str = "DAY", timestamp: datetime = None) -> Dict[str, Any]:
        """
        Simulates order execution with TP/SL storage.
        """
        if qty <= 0:
            raise ValueError("Quantity must be positive")

        current_price = fetch_current_price(symbol)
        if current_price == 0:
             print(f"Error: Could not fetch price for {symbol}. Order rejected.")
             return {"status": "rejected", "reason": "Price unavailable", "symbol": symbol}

        if timestamp is None:
            timestamp = datetime.now()
            
        timestamp_str = timestamp.isoformat()
        cost = current_price * qty

        if side == "buy":
            # Check Buying Power
            account = self.get_account()
            if cost > account["buying_power"]:
                print(f"Order Rejected: Insufficient Buying Power. Cost: {cost}, BP: {account['buying_power']}")
                return {"status": "rejected", "reason": "Insufficient Buying Power"}

            # Execute Buy
            self.state["cash"] -= cost
            
            if symbol not in self.state["positions"]:
                self.state["positions"][symbol] = {
                    "qty": 0, 
                    "avg_entry_price": 0.0,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "time_horizon": time_horizon
                }
            
            pos = self.state["positions"][symbol]
            new_qty = pos["qty"] + qty
            new_avg = ((pos["qty"] * pos["avg_entry_price"]) + cost) / new_qty
            
            # Update Position
            self.state["positions"][symbol].update({
                "qty": new_qty,
                "avg_entry_price": new_avg,
                "stop_loss": stop_loss, # Update SL/TP to latest order's preference
                "take_profit": take_profit,
                "time_horizon": time_horizon
            })
            
        elif side == "sell":
            if symbol not in self.state["positions"] or self.state["positions"][symbol]["qty"] < qty:
                print(f"Order Rejected: Insufficient shares to sell {symbol}")
                return {"status": "rejected", "reason": "Insufficient shares"}
            
            # Execute Sell
            revenue = current_price * qty
            self.state["cash"] += revenue
            
            self.state["positions"][symbol]["qty"] -= qty
            if self.state["positions"][symbol]["qty"] == 0:
                del self.state["positions"][symbol]

        # Log Order
        order_details = {
            "id": f"mock_order_{len(self.state['orders']) + 1}",
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": type,
            "filled_avg_price": current_price,
            "status": "filled",
            "submitted_at": timestamp_str,
            "filled_at": timestamp_str,
            "tp": take_profit,
            "sl": stop_loss,
            "horizon": time_horizon
        }
        self.state["orders"].append(order_details)
        self._save_state()
        
        print(f"MOCK ORDER FILLED: {side.upper()} {qty} {symbol} @ ${current_price:.2f} (TP: {take_profit}, SL: {stop_loss})")
        return order_details

    def update_prices(self, market_data: Dict[str, float]):
        """Updates internal state with latest prices (for P&L tracking)."""
        # In a real broker, this might not be needed as they track it, 
        # but for Mock, we can use this to trigger checks or just update equity.
        self._update_equity() # This fetches prices internally in current implementation, 
                              # but we can optimize to use passed market_data if we want.
        pass

    def check_triggers(self, market_data: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """Checks TP/SL triggers."""
        triggered_orders = []
        
        # Iterate over copy
        for symbol, pos in list(self.state["positions"].items()):
            qty = pos["qty"]
            if qty == 0: continue
            
            # Determine Current Price
            current_price = None
            
            # If market_data is provided (Simulation or explicit update), use it
            if market_data is not None:
                current_price = market_data.get(symbol)
                # STRICT FAIL-SAFE: If we are in simulation (market_data provided) and price is missing/invalid, ABORT.
                if current_price is None or current_price <= 0:
                    raise RuntimeError(f"CRITICAL FAIL-SAFE: Missing price data for {symbol} during simulation. Aborting to prevent false execution.")
            else:
                # Real-time mode (no market_data passed), fetch live
                current_price = fetch_current_price(symbol) 
            
            # Check for invalid price (None or <= 0) - Double check
            if current_price is None or current_price <= 0:
                 # In Real-time, we might skip. In Sim, we already raised.
                 continue
            
            # Update internal price for display
            self.state["positions"][symbol]["current_price"] = current_price
            
            tp = pos.get("take_profit")
            sl = pos.get("stop_loss")
            
            reason = None
            if tp and current_price >= tp:
                reason = f"Take Profit Hit ({current_price} >= {tp})"
            elif sl and current_price <= sl:
                reason = f"Stop Loss Hit ({current_price} <= {sl})"
                
            if reason:
                print(f"TRIGGER: {reason} for {symbol}")
                order = self.submit_order(symbol, qty, "sell")
                order["reason"] = reason
                triggered_orders.append(order)
                
        return triggered_orders

    def close_all_positions(self) -> List[Dict[str, Any]]:
        print("Liquidating all positions...")
        results = []
        # Create a copy of keys to iterate safely while modifying
        symbols = list(self.state["positions"].keys())
        
        for symbol in symbols:
            qty = self.state["positions"][symbol]["qty"]
            if qty > 0:
                res = self.submit_order(symbol, qty, "sell")
                results.append(res)
        
        return results
