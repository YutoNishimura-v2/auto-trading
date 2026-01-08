from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BrokerClient(ABC):
    """
    Abstract Base Class for a Broker Client.
    Modeled after Alpaca API structure.
    """

    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        """
        Returns account information.
        Expected keys: 'cash', 'portfolio_value', 'buying_power', 'equity'.
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Returns a list of open positions.
        Each position should have: 'symbol', 'qty', 'avg_entry_price', 'current_price', 'market_value'.
        """
        pass

    @abstractmethod
    def submit_order(self, symbol: str, qty: int, side: str, type: str = "market", time_in_force: str = "day", 
                     stop_loss: float = None, take_profit: float = None, time_horizon: str = "DAY") -> Dict[str, Any]:
        """
        Submits an order with optional TP/SL and Time Horizon.
        """
        pass

    @abstractmethod
    def update_prices(self, market_data: Dict[str, float]):
        """
        Updates the current prices of held positions for P&L calculation and Trigger checks.
        Args:
            market_data: Dict of {symbol: current_price}
        """
        pass

    @abstractmethod
    def check_triggers(self, market_data: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """
        Checks if any TP/SL triggers have been hit based on latest prices.
        Returns list of executed orders (exits).
        """
        pass

    @abstractmethod
    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Liquidates all open positions.
        Returns list of order results.
        """
        pass
